-- =====================================================================
-- PIA Base de Datos - Equipo 3 - Telemedicina y Consultas Virtuales
-- Gestor: MySQL 8.x (probado también en MariaDB 10.11)
-- Ejecutar con:  mysql -u root -p < telemedicina.sql
-- =====================================================================

SET NAMES utf8mb4;   -- evita problemas con acentos al cargar el script
DROP DATABASE IF EXISTS telemedicina;
CREATE DATABASE telemedicina
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE telemedicina;

-- ---------------------------------------------------------------------
-- 1. ESTRUCTURA (DDL)
-- ---------------------------------------------------------------------

CREATE TABLE usuario (
    id_usuario  INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    nombre      VARCHAR(100)  NOT NULL,
    correo      VARCHAR(120)  NOT NULL,
    rol         ENUM('Paciente','Admin','Soporte') NOT NULL DEFAULT 'Paciente',
    estado      ENUM('Activo','Inactivo')          NOT NULL DEFAULT 'Activo',
    PRIMARY KEY (id_usuario),
    UNIQUE KEY uq_usuario_correo (correo)
) ENGINE=InnoDB;

CREATE TABLE medico (
    id_medico     INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre        VARCHAR(100) NOT NULL,
    correo        VARCHAR(120) NOT NULL,
    especialidad  VARCHAR(80)  NOT NULL,
    estado        ENUM('Activo','Inactivo') NOT NULL DEFAULT 'Activo',
    PRIMARY KEY (id_medico),
    UNIQUE KEY uq_medico_correo (correo)
) ENGINE=InnoDB;

CREATE TABLE consulta (
    id_consulta   INT UNSIGNED NOT NULL AUTO_INCREMENT,
    motivo        VARCHAR(200) NOT NULL,
    diagnostico   VARCHAR(255) NOT NULL DEFAULT 'Pendiente',
    estado        ENUM('Programada','En Curso','Finalizada','Cancelada')
                  NOT NULL DEFAULT 'Programada',
    modalidad     ENUM('Video','Chat')               NOT NULL,
    prioridad     ENUM('Baja','Normal','Alta')       NOT NULL DEFAULT 'Normal',
    fecha_inicio  DATETIME     NULL,
    fecha_fin     DATETIME     NULL,
    id_usuario    INT UNSIGNED NOT NULL,          -- paciente
    id_medico     INT UNSIGNED NULL,              -- NULL = aún sin médico asignado
    PRIMARY KEY (id_consulta),
    CONSTRAINT fk_consulta_usuario FOREIGN KEY (id_usuario)
        REFERENCES usuario (id_usuario) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_consulta_medico FOREIGN KEY (id_medico)
        REFERENCES medico (id_medico) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_consulta_fechas
        CHECK (fecha_fin IS NULL OR fecha_inicio IS NULL OR fecha_fin >= fecha_inicio)
) ENGINE=InnoDB;

CREATE TABLE expediente_adjunto (
    id_documento  INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre        VARCHAR(120) NOT NULL,
    tipo          ENUM('Receta','Examen','Imagen_Diagnostica') NOT NULL,
    url_ruta      VARCHAR(255) NOT NULL,
    fecha_carga   DATE         NOT NULL,
    id_consulta   INT UNSIGNED NOT NULL,
    PRIMARY KEY (id_documento),
    CONSTRAINT fk_adjunto_consulta FOREIGN KEY (id_consulta)
        REFERENCES consulta (id_consulta) ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE indicador (
    id_indicador  INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre        VARCHAR(80)  NOT NULL,
    descripcion   VARCHAR(255) NOT NULL,
    tipo          VARCHAR(40)  NOT NULL,
    formula       VARCHAR(120) NOT NULL,
    unidad        VARCHAR(20)  NOT NULL,
    estado        ENUM('Activo','Inactivo') NOT NULL DEFAULT 'Activo',
    PRIMARY KEY (id_indicador),
    UNIQUE KEY uq_indicador_nombre (nombre)
) ENGINE=InnoDB;

CREATE TABLE consulta_indicador (
    id_consulta       INT UNSIGNED NOT NULL,
    id_indicador      INT UNSIGNED NOT NULL,
    fecha_asignacion  DATE         NOT NULL,
    valor             DECIMAL(10,2) NULL,        -- resultado medido del indicador
    PRIMARY KEY (id_consulta, id_indicador),     -- llave primaria compuesta
    CONSTRAINT fk_ci_consulta FOREIGN KEY (id_consulta)
        REFERENCES consulta (id_consulta) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_ci_indicador FOREIGN KEY (id_indicador)
        REFERENCES indicador (id_indicador) ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Regla de negocio: solo un usuario con rol Paciente puede tener consultas
DELIMITER $$
CREATE TRIGGER trg_consulta_paciente_ins BEFORE INSERT ON consulta
FOR EACH ROW
BEGIN
    IF (SELECT rol FROM usuario WHERE id_usuario = NEW.id_usuario) <> 'Paciente' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Solo un usuario con rol Paciente puede tener consultas';
    END IF;
END$$

CREATE TRIGGER trg_consulta_paciente_upd BEFORE UPDATE ON consulta
FOR EACH ROW
BEGIN
    IF (SELECT rol FROM usuario WHERE id_usuario = NEW.id_usuario) <> 'Paciente' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Solo un usuario con rol Paciente puede tener consultas';
    END IF;
END$$
DELIMITER ;

-- ---------------------------------------------------------------------
-- 2. DATOS DE EJEMPLO (ficticios)
-- ---------------------------------------------------------------------

INSERT INTO usuario (nombre, correo, rol, estado) VALUES
 ('Ana Torres',     'ana.torres@example.com',     'Paciente', 'Activo'),
 ('Luis Herrera',   'luis.herrera@example.com',   'Paciente', 'Activo'),
 ('Marta Salinas',  'marta.salinas@example.com',  'Paciente', 'Activo'),
 ('Pedro Admin',    'pedro.admin@example.com',    'Admin',    'Activo'),
 ('Sofía Soporte',  'sofia.soporte@example.com',  'Soporte',  'Activo');

INSERT INTO medico (nombre, correo, especialidad, estado) VALUES
 ('Laura Méndez',   'laura.mendez@example.com',   'Medicina general', 'Activo'),
 ('Carlos Ibarra',  'carlos.ibarra@example.com',  'Cardiología',      'Activo'),
 ('Elena Robles',   'elena.robles@example.com',   'Dermatología',     'Inactivo');

INSERT INTO consulta
 (motivo, diagnostico, estado, modalidad, prioridad, fecha_inicio, fecha_fin, id_usuario, id_medico) VALUES
 ('Seguimiento médico', 'Pendiente', 'Programada', 'Video', 'Normal',
  '2026-10-30 10:00:00', NULL, 1, 1),
 ('Dolor de pecho leve', 'Estrés sin hallazgos cardiacos', 'Finalizada', 'Video', 'Alta',
  '2026-10-26 09:00:00', '2026-10-26 09:25:00', 2, 2),
 ('Revisión de resultados de laboratorio', 'Valores dentro de lo normal', 'Finalizada', 'Chat', 'Normal',
  '2026-10-27 16:00:00', '2026-10-27 16:12:00', 1, 1),
 ('Consulta por alergia en la piel', 'Pendiente', 'Programada', 'Chat', 'Baja',
  '2026-11-02 12:00:00', NULL, 3, NULL);

INSERT INTO expediente_adjunto (nombre, tipo, url_ruta, fecha_carga, id_consulta) VALUES
 ('Resultado de laboratorio', 'Examen',             '/expedientes/examen_001.pdf',  '2026-10-26', 1),
 ('Receta electrónica',       'Receta',             '/expedientes/receta_002.pdf',  '2026-10-26', 2),
 ('Electrocardiograma',       'Imagen_Diagnostica', '/expedientes/ecg_002.png',     '2026-10-26', 2),
 ('Biometría hemática',       'Examen',             '/expedientes/examen_003.pdf',  '2026-10-27', 3);

INSERT INTO indicador (nombre, descripcion, tipo, formula, unidad, estado) VALUES
 ('Duración de consulta',        'Tiempo que dura la consulta',                 'Tiempo',       'Tiempo fin - inicio',                    'min',    'Activo'),
 ('Tiempo de espera',            'Minutos entre la hora programada y el inicio', 'Tiempo',       'Hora de inicio real - hora programada',  'min',    'Activo'),
 ('Satisfacción del paciente',   'Calificación que otorga el paciente',          'Satisfacción', 'Promedio de la calificación (1 a 10)',   'puntos', 'Activo');

INSERT INTO consulta_indicador (id_consulta, id_indicador, fecha_asignacion, valor) VALUES
 (1, 1, '2026-10-26', NULL),
 (2, 1, '2026-10-26', 25.00),
 (2, 3, '2026-10-26',  9.00),
 (3, 1, '2026-10-27', 12.00),
 (3, 2, '2026-10-27',  4.00),
 (3, 3, '2026-10-27',  8.00);

-- ---------------------------------------------------------------------
-- 3. VISTAS Y CONSULTAS
-- ---------------------------------------------------------------------

-- Historial de consultas con paciente y médico
CREATE VIEW v_historial_consultas AS
SELECT c.id_consulta,
       u.nombre        AS paciente,
       IFNULL(m.nombre, 'Sin asignar') AS medico,
       m.especialidad,
       c.motivo, c.diagnostico, c.estado, c.modalidad, c.prioridad,
       c.fecha_inicio, c.fecha_fin
FROM consulta c
JOIN usuario u      ON u.id_usuario = c.id_usuario
LEFT JOIN medico m  ON m.id_medico  = c.id_medico;

-- Duración calculada con la fórmula del indicador (fin - inicio)
CREATE VIEW v_duracion_consulta AS
SELECT id_consulta,
       TIMESTAMPDIFF(MINUTE, fecha_inicio, fecha_fin) AS duracion_min
FROM consulta
WHERE fecha_inicio IS NOT NULL AND fecha_fin IS NOT NULL;

-- Q1. Historial completo
-- SELECT * FROM v_historial_consultas ORDER BY fecha_inicio;

-- Q2. Consultas de un paciente con sus documentos
-- SELECT c.id_consulta, c.motivo, e.nombre AS documento, e.tipo, e.fecha_carga
-- FROM consulta c LEFT JOIN expediente_adjunto e ON e.id_consulta = c.id_consulta
-- WHERE c.id_usuario = 1;

-- Q3. Indicadores medidos por consulta
-- SELECT c.id_consulta, i.nombre, ci.valor, i.unidad
-- FROM consulta_indicador ci
-- JOIN consulta c   ON c.id_consulta  = ci.id_consulta
-- JOIN indicador i  ON i.id_indicador = ci.id_indicador
-- ORDER BY c.id_consulta;

-- Q4. Promedio de satisfacción por médico
-- SELECT m.nombre, ROUND(AVG(ci.valor),1) AS satisfaccion_prom
-- FROM consulta_indicador ci
-- JOIN indicador i ON i.id_indicador = ci.id_indicador AND i.nombre = 'Satisfacción del paciente'
-- JOIN consulta c  ON c.id_consulta  = ci.id_consulta
-- JOIN medico m    ON m.id_medico    = c.id_medico
-- GROUP BY m.id_medico, m.nombre;