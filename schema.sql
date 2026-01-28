PRAGMA foreign_keys = ON;

-- =========================
-- TABLA: comites
-- =========================
CREATE TABLE IF NOT EXISTS comites (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL UNIQUE
);

-- =========================
-- TABLA: usuarios
-- =========================
CREATE TABLE IF NOT EXISTS usuarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL,
  usuario TEXT NOT NULL UNIQUE,
  clave TEXT NOT NULL,
  rol TEXT NOT NULL CHECK(rol IN ('ADMIN','OPERADOR')),
  activo INTEGER NOT NULL DEFAULT 1,
  comite_id INTEGER NULL,
  FOREIGN KEY (comite_id) REFERENCES comites(id) ON UPDATE CASCADE ON DELETE SET NULL
);

-- =========================
-- TABLA: categorias
-- =========================
CREATE TABLE IF NOT EXISTS categorias (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL UNIQUE
);

-- =========================
-- TABLA: ubicaciones
-- =========================
CREATE TABLE IF NOT EXISTS ubicaciones (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL UNIQUE
);

-- =========================
-- TABLA: responsables
-- =========================
CREATE TABLE IF NOT EXISTS responsables (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL UNIQUE
);

-- =========================
-- TABLA: activos
-- =========================
CREATE TABLE IF NOT EXISTS activos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  codigo TEXT UNIQUE,
  nombre TEXT NOT NULL,
  descripcion TEXT,
  estado TEXT NOT NULL DEFAULT 'ACTIVO' CHECK(estado IN ('ACTIVO','REPARACION','BAJA')),
  fecha_registro TEXT DEFAULT (datetime('now')),

  categoria_id INTEGER NULL,
  ubicacion_id INTEGER NULL,
  responsable_id INTEGER NULL,
  comite_id INTEGER NOT NULL,

  FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON UPDATE CASCADE ON DELETE SET NULL,
  FOREIGN KEY (ubicacion_id) REFERENCES ubicaciones(id) ON UPDATE CASCADE ON DELETE SET NULL,
  FOREIGN KEY (responsable_id) REFERENCES responsables(id) ON UPDATE CASCADE ON DELETE SET NULL,
  FOREIGN KEY (comite_id) REFERENCES comites(id) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- =========================
-- TABLA: movimientos
-- =========================
CREATE TABLE IF NOT EXISTS movimientos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  activo_id INTEGER NOT NULL,
  fecha TEXT DEFAULT (datetime('now')),
  tipo TEXT NOT NULL,
  detalle TEXT,
  FOREIGN KEY (activo_id) REFERENCES activos(id) ON UPDATE CASCADE ON DELETE CASCADE
);
