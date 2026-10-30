"""
Sistema de Telemedicina y Consultas Virtuales - PIA Base de Datos (Equipo 3)
Aplicación web: FastAPI + MySQL.

Ejecutar:
    pip install -r requirements.txt
    uvicorn app:app --reload
Abrir:  http://127.0.0.1:8000

Variables de entorno opcionales: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
"""
import os
from datetime import date
from typing import Optional

import mysql.connector
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="Telemedicina y Consultas Virtuales")

DB_CONFIG = dict(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", "CompilandoRico0w0"),
    database=os.getenv("DB_NAME", "telemedicina"),
)


# ----------------------------------------------------------------------
# Acceso a datos
# ----------------------------------------------------------------------
def ejecutar(sql: str, params: tuple = (), escribir: bool = False):
    """Ejecuta una sentencia con parámetros (evita inyección SQL).
    Devuelve filas (SELECT) o el id insertado (INSERT)."""
    conn = mysql.connector.connect(**DB_CONFIG)
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        if escribir:
            conn.commit()
            return cur.lastrowid
        return cur.fetchall()
    except mysql.connector.Error as e:
        # Las restricciones de la BD (FK, UNIQUE, CHECK, triggers) llegan aquí
        raise HTTPException(status_code=400, detail=e.msg)
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Modelos de entrada
# ----------------------------------------------------------------------
class ConsultaIn(BaseModel):
    motivo: str
    modalidad: str                       # Video | Chat
    prioridad: str = "Normal"            # Baja | Normal | Alta
    fecha_inicio: Optional[str] = None   # 'YYYY-MM-DD HH:MM:SS'
    id_usuario: int
    id_medico: Optional[int] = None


class EstadoIn(BaseModel):
    estado: str                          # Programada | En Curso | Finalizada | Cancelada
    diagnostico: Optional[str] = None
    fecha_fin: Optional[str] = None


class DocumentoIn(BaseModel):
    nombre: str
    tipo: str                            # Receta | Examen | Imagen_Diagnostica
    url_ruta: str


class AsignacionIn(BaseModel):
    id_indicador: int
    valor: Optional[float] = None


# ----------------------------------------------------------------------
# API REST
# ----------------------------------------------------------------------
@app.get("/api/pacientes")
def pacientes():
    return ejecutar("SELECT id_usuario, nombre FROM usuario "
                    "WHERE rol='Paciente' AND estado='Activo' ORDER BY nombre")


@app.get("/api/medicos")
def medicos():
    return ejecutar("SELECT id_medico, nombre, especialidad FROM medico "
                    "WHERE estado='Activo' ORDER BY nombre")


@app.get("/api/indicadores")
def indicadores():
    return ejecutar("SELECT id_indicador, nombre, unidad FROM indicador "
                    "WHERE estado='Activo' ORDER BY nombre")


@app.get("/api/consultas")
def historial():
    filas = ejecutar("SELECT * FROM v_historial_consultas ORDER BY id_consulta DESC")
    for f in filas:  # fechas a texto para JSON
        for k in ("fecha_inicio", "fecha_fin"):
            f[k] = str(f[k]) if f[k] else None
    return filas


@app.post("/api/consultas", status_code=201)
def crear_consulta(c: ConsultaIn):
    nuevo = ejecutar(
        "INSERT INTO consulta (motivo, modalidad, prioridad, fecha_inicio, id_usuario, id_medico) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (c.motivo, c.modalidad, c.prioridad, c.fecha_inicio, c.id_usuario, c.id_medico),
        escribir=True)
    return {"id_consulta": nuevo}


@app.patch("/api/consultas/{id_consulta}/estado")
def cambiar_estado(id_consulta: int, e: EstadoIn):
    ejecutar("UPDATE consulta SET estado=%s, diagnostico=COALESCE(%s, diagnostico), "
             "fecha_fin=COALESCE(%s, fecha_fin) WHERE id_consulta=%s",
             (e.estado, e.diagnostico, e.fecha_fin, id_consulta), escribir=True)
    return {"ok": True}


@app.get("/api/consultas/{id_consulta}/documentos")
def listar_documentos(id_consulta: int):
    filas = ejecutar("SELECT id_documento, nombre, tipo, url_ruta, fecha_carga "
                     "FROM expediente_adjunto WHERE id_consulta=%s ORDER BY id_documento",
                     (id_consulta,))
    for f in filas:
        f["fecha_carga"] = str(f["fecha_carga"])
    return filas


@app.post("/api/consultas/{id_consulta}/documentos", status_code=201)
def agregar_documento(id_consulta: int, d: DocumentoIn):
    nuevo = ejecutar(
        "INSERT INTO expediente_adjunto (nombre, tipo, url_ruta, fecha_carga, id_consulta) "
        "VALUES (%s, %s, %s, %s, %s)",
        (d.nombre, d.tipo, d.url_ruta, date.today().isoformat(), id_consulta),
        escribir=True)
    return {"id_documento": nuevo}


@app.get("/api/consultas/{id_consulta}/indicadores")
def indicadores_de_consulta(id_consulta: int):
    filas = ejecutar(
        "SELECT i.nombre, ci.valor, i.unidad, ci.fecha_asignacion "
        "FROM consulta_indicador ci JOIN indicador i ON i.id_indicador = ci.id_indicador "
        "WHERE ci.id_consulta=%s ORDER BY i.nombre", (id_consulta,))
    for f in filas:
        f["fecha_asignacion"] = str(f["fecha_asignacion"])
        f["valor"] = float(f["valor"]) if f["valor"] is not None else None
    return filas


@app.post("/api/consultas/{id_consulta}/indicadores", status_code=201)
def asignar_indicador(id_consulta: int, a: AsignacionIn):
    ejecutar("INSERT INTO consulta_indicador (id_consulta, id_indicador, fecha_asignacion, valor) "
             "VALUES (%s, %s, %s, %s)",
             (id_consulta, a.id_indicador, date.today().isoformat(), a.valor), escribir=True)
    return {"ok": True}


# ----------------------------------------------------------------------
# Interfaz web (una sola página)
# ----------------------------------------------------------------------
PAGINA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Telemedicina y Consultas Virtuales</title>
<style>
 body{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f3f6fa;color:#1f2a37}
 header{background:#1f4e79;color:#fff;padding:14px 24px}
 main{max-width:1100px;margin:20px auto;padding:0 16px}
 section{background:#fff;border-radius:8px;padding:16px 20px;margin-bottom:18px;box-shadow:0 1px 3px #0002}
 h2{margin-top:0;font-size:18px;color:#1f4e79}
 table{border-collapse:collapse;width:100%;font-size:14px}
 th,td{border-bottom:1px solid #dde3ea;padding:6px 8px;text-align:left}
 th{background:#e8eef5}
 label{display:block;margin:8px 0 2px;font-size:13px}
 input,select,button{padding:7px;font-size:14px;border:1px solid #b8c2cc;border-radius:5px}
 button{background:#1f4e79;color:#fff;border:0;cursor:pointer;margin-top:10px}
 .fila{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
 #msg{padding:8px 12px;border-radius:5px;display:none;margin-bottom:12px}
 .ok{background:#d9f2e0}.err{background:#fbdcdc}
 .link{color:#1f4e79;cursor:pointer;text-decoration:underline}
</style></head><body>
<header><h1 style="margin:0;font-size:22px">Telemedicina y Consultas Virtuales</h1></header>
<main>
<div id="msg"></div>

<section><h2>Nueva consulta</h2>
 <div class="fila">
  <div><label>Paciente</label><select id="n_paciente"></select></div>
  <div><label>Médico (opcional)</label><select id="n_medico"></select></div>
  <div><label>Modalidad</label><select id="n_modalidad"><option>Video</option><option>Chat</option></select></div>
  <div><label>Prioridad</label><select id="n_prioridad"><option>Baja</option><option selected>Normal</option><option>Alta</option></select></div>
  <div><label>Fecha y hora</label><input type="datetime-local" id="n_fecha"></div>
  <div><label>Motivo</label><input id="n_motivo" style="width:100%"></div>
 </div>
 <button onclick="crearConsulta()">Registrar consulta</button>
</section>

<section><h2>Historial de consultas</h2>
 <table><thead><tr><th>#</th><th>Paciente</th><th>Médico</th><th>Motivo</th><th>Estado</th><th>Modalidad</th><th>Prioridad</th><th>Inicio</th><th></th></tr></thead>
 <tbody id="tabla"></tbody></table>
</section>

<section id="detalle" style="display:none"><h2 id="det_titulo"></h2>
 <h3>Expediente adjunto</h3>
 <table><thead><tr><th>Documento</th><th>Tipo</th><th>Ruta</th><th>Cargado</th></tr></thead><tbody id="docs"></tbody></table>
 <div class="fila">
  <div><label>Nombre</label><input id="d_nombre"></div>
  <div><label>Tipo</label><select id="d_tipo"><option>Receta</option><option>Examen</option><option>Imagen_Diagnostica</option></select></div>
  <div><label>Ruta</label><input id="d_ruta" placeholder="/expedientes/archivo.pdf"></div>
 </div><button onclick="agregarDoc()">Agregar documento</button>
 <h3>Indicadores</h3>
 <table><thead><tr><th>Indicador</th><th>Valor</th><th>Unidad</th><th>Asignado</th></tr></thead><tbody id="inds"></tbody></table>
 <div class="fila">
  <div><label>Indicador</label><select id="i_ind"></select></div>
  <div><label>Valor</label><input type="number" step="0.01" id="i_valor"></div>
 </div><button onclick="asignarInd()">Asignar indicador</button>
</section>
</main>
<script>
let actual=null;
const $=id=>document.getElementById(id);
function aviso(t,ok=true){const m=$('msg');m.textContent=t;m.className=ok?'ok':'err';m.style.display='block';setTimeout(()=>m.style.display='none',4000)}
async function api(url,metodo='GET',cuerpo){
  const r=await fetch(url,{method:metodo,headers:{'Content-Type':'application/json'},body:cuerpo?JSON.stringify(cuerpo):undefined});
  const d=await r.json(); if(!r.ok) throw new Error(d.detail||'Error'); return d;}
function opciones(sel,lista,v,t,vacio){$(sel).innerHTML=(vacio?'<option value="">'+vacio+'</option>':'')+lista.map(x=>`<option value="${x[v]}">${x[t]}</option>`).join('')}
async function cargarCatalogos(){
  opciones('n_paciente',await api('/api/pacientes'),'id_usuario','nombre');
  opciones('n_medico',(await api('/api/medicos')).map(m=>({...m,t:m.nombre+' ('+m.especialidad+')'})),'id_medico','t','Sin asignar');
  opciones('i_ind',await api('/api/indicadores'),'id_indicador','nombre');}
async function cargarHistorial(){
  const f=await api('/api/consultas');
  $('tabla').innerHTML=f.map(c=>`<tr><td>${c.id_consulta}</td><td>${c.paciente}</td><td>${c.medico}</td><td>${c.motivo}</td><td>${c.estado}</td><td>${c.modalidad}</td><td>${c.prioridad}</td><td>${c.fecha_inicio||''}</td><td><span class="link" onclick="ver(${c.id_consulta})">Detalle</span></td></tr>`).join('');}
async function crearConsulta(){
  try{
    const f=$('n_fecha').value;
    await api('/api/consultas','POST',{motivo:$('n_motivo').value,modalidad:$('n_modalidad').value,prioridad:$('n_prioridad').value,
      fecha_inicio:f?f.replace('T',' ')+':00':null,id_usuario:+$('n_paciente').value,id_medico:$('n_medico').value?+$('n_medico').value:null});
    aviso('Consulta registrada');$('n_motivo').value='';cargarHistorial();
  }catch(e){aviso(e.message,false)}}
async function ver(id){
  actual=id;$('detalle').style.display='block';$('det_titulo').textContent='Consulta #'+id;
  const d=await api(`/api/consultas/${id}/documentos`);
  $('docs').innerHTML=d.map(x=>`<tr><td>${x.nombre}</td><td>${x.tipo}</td><td>${x.url_ruta}</td><td>${x.fecha_carga}</td></tr>`).join('')||'<tr><td colspan=4>Sin documentos</td></tr>';
  const i=await api(`/api/consultas/${id}/indicadores`);
  $('inds').innerHTML=i.map(x=>`<tr><td>${x.nombre}</td><td>${x.valor??'—'}</td><td>${x.unidad}</td><td>${x.fecha_asignacion}</td></tr>`).join('')||'<tr><td colspan=4>Sin indicadores</td></tr>';
  $('detalle').scrollIntoView();}
async function agregarDoc(){
  try{await api(`/api/consultas/${actual}/documentos`,'POST',{nombre:$('d_nombre').value,tipo:$('d_tipo').value,url_ruta:$('d_ruta').value});
    aviso('Documento agregado');ver(actual);}catch(e){aviso(e.message,false)}}
async function asignarInd(){
  try{const v=$('i_valor').value;
    await api(`/api/consultas/${actual}/indicadores`,'POST',{id_indicador:+$('i_ind').value,valor:v===''?null:+v});
    aviso('Indicador asignado');ver(actual);}catch(e){aviso(e.message,false)}}
cargarCatalogos().then(cargarHistorial);
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def inicio():
    return PAGINA