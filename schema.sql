-- =========================
-- RAP Amazonía - Schema PostgreSQL
-- =========================

-- TABLA: comites
CREATE TABLE IF NOT EXISTS comites (
  id SERIAL PRIMARY KEY,
  nombre TEXT NOT NULL UNIQUE
);

-- TABLA: usuarios
CREATE TABLE IF NOT EXISTS usuarios (
  id SERIAL PRIMARY KEY,
  nombre TEXT NOT NULL,
  usuario TEXT NOT NULL UNIQUE,
  clave TEXT NOT NULL,
  rol TEXT NOT NULL CHECK (rol IN ('ADMIN','OPERADOR')),
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  comite_id INTEGER NULL,
  CONSTRAINT fk_usuarios_comite
    FOREIGN KEY (comite_id) REFERENCES comites(id)
    ON UPDATE CASCADE
    ON DELETE SET NULL
);

-- TABLA: categorias
CREATE TABLE IF NOT EXISTS categorias (
  id SERIAL PRIMARY KEY,
  nombre TEXT NOT NULL UNIQUE
);

-- TABLA: ubicaciones
CREATE TABLE IF NOT EXISTS ubicaciones (
  id SERIAL PRIMARY KEY,
  nombre TEXT NOT NULL UNIQUE
);

-- TABLA: responsables
CREATE TABLE IF NOT EXISTS responsables (
  id SERIAL PRIMARY KEY,
  nombre TEXT NOT NULL UNIQUE
);

-- TABLA: activos
CREATE TABLE IF NOT EXISTS activos (
  id SERIAL PRIMARY KEY,
  codigo TEXT UNIQUE,
  nombre TEXT NOT NULL,
  descripcion TEXT,
  estado TEXT NOT NULL DEFAULT 'ACTIVO' CHECK (estado IN ('ACTIVO','REPARACION','BAJA')),
  fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  categoria_id INTEGER NULL,
  ubicacion_id INTEGER NULL,
  responsable_id INTEGER NULL,
  comite_id INTEGER NOT NULL,

  CONSTRAINT fk_activos_categoria
    FOREIGN KEY (categoria_id) REFERENCES categorias(id)
    ON UPDATE CASCADE
    ON DELETE SET NULL,

  CONSTRAINT fk_activos_ubicacion
    FOREIGN KEY (ubicacion_id) REFERENCES ubicaciones(id)
    ON UPDATE CASCADE
    ON DELETE SET NULL,

  CONSTRAINT fk_activos_responsable
    FOREIGN KEY (responsable_id) REFERENCES responsables(id)
    ON UPDATE CASCADE
    ON DELETE SET NULL,

  CONSTRAINT fk_activos_comite
    FOREIGN KEY (comite_id) REFERENCES comites(id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
);

-- TABLA: movimientos
CREATE TABLE IF NOT EXISTS movimientos (
  id SERIAL PRIMARY KEY,
  activo_id INTEGER NOT NULL,
  fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  tipo TEXT NOT NULL,
  detalle TEXT,

  CONSTRAINT fk_mov_activo
    FOREIGN KEY (activo_id) REFERENCES activos(id)
    ON UPDATE CASCADE
    ON DELETE CASCADE
);

-- Índices útiles (opcional pero recomendado)
CREATE INDEX IF NOT EXISTS idx_activos_comite ON activos(comite_id);
CREATE INDEX IF NOT EXISTS idx_activos_estado ON activos(estado);
CREATE INDEX IF NOT EXISTS idx_activos_codigo ON activos(codigo);
