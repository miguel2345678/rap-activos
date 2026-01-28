import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

# =========================
# Compatibilidad con tu proyecto
# =========================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

def _normalize_dsn(dsn: str) -> str:
    # Railway a veces da postgres:// y psycopg prefiere postgresql://
    if dsn and dsn.startswith("postgres://"):
        return "postgresql://" + dsn[len("postgres://") :]
    return dsn

def _build_local_dsn() -> str:
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "rap_activos")
    user = os.getenv("DB_USER", "postgres")
    pwd  = os.getenv("DB_PASSWORD", "")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{name}"

# Para tu ver_db.py (solo imprime)
DB_PATH = _normalize_dsn(os.getenv("DATABASE_URL", _build_local_dsn()))

def get_conn():
    """
    Conecta a Postgres:
    - En Railway: usa DATABASE_URL
    - Local: usa DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD (o defaults)
    """
    dsn = _normalize_dsn(os.getenv("DATABASE_URL"))
    if not dsn:
        dsn = _build_local_dsn()

    # En Railway casi siempre debes usar SSL
    # (si no hace falta, no pasa nada, psycopg negocia)
    sslmode = os.getenv("PGSSLMODE", "require") if os.getenv("DATABASE_URL") else os.getenv("PGSSLMODE", "prefer")

    return psycopg.connect(
        dsn,
        row_factory=dict_row,
        sslmode=sslmode,
    )

def qone(sql: str, params=()):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()

def qall(sql: str, params=()):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()

def exec_sql(sql: str, params=()):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)

            last = None
            # Si el INSERT trae RETURNING id, lo capturamos
            try:
                r = cur.fetchone()
                if r and "id" in r:
                    last = r["id"]
            except Exception:
                pass

        conn.commit()
        return last
    finally:
        conn.close()

def init_db():
    """
    En Railway NO leemos schema.sql automáticamente aquí.
    (Se crean tablas una vez en la DB de Railway y listo)
    Aquí solo hacemos SEED si está vacío.
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # 1) Seed comités
            comites = [
                "Control interno",
                "Direccion de planeacion",
                "Direccion financiera",
                "Gerencia",
                "Secretaria general y juridica",
                "Oficina de talento humano",
            ]

            cur.execute("SELECT COUNT(*) AS n FROM comites")
            total_comites = cur.fetchone()["n"]

            if total_comites == 0:
                for c in comites:
                    cur.execute(
                        "INSERT INTO comites(nombre) VALUES (%s) ON CONFLICT DO NOTHING",
                        (c,),
                    )

            # 2) Seed catálogos
            categorias = ["Equipos TI", "Mobiliario", "Herramientas"]
            ubicaciones = ["Sede Principal", "Administración", "Planeación"]
            responsables = ["Sin asignar", "Administrador RAP"]

            for c in categorias:
                cur.execute("INSERT INTO categorias(nombre) VALUES (%s) ON CONFLICT DO NOTHING", (c,))
            for u in ubicaciones:
                cur.execute("INSERT INTO ubicaciones(nombre) VALUES (%s) ON CONFLICT DO NOTHING", (u,))
            for r in responsables:
                cur.execute("INSERT INTO responsables(nombre) VALUES (%s) ON CONFLICT DO NOTHING", (r,))

            # 3) Admin + Operador demo
            cur.execute("SELECT id FROM comites WHERE nombre=%s", ("Control interno",))
            row = cur.fetchone()
            default_comite_id = row["id"] if row else None

            cur.execute(
                """
                INSERT INTO usuarios(nombre, usuario, clave, rol, comite_id)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (usuario) DO NOTHING
                """,
                ("Admin RAP", "admin", "admin123", "ADMIN", None),
            )

            cur.execute(
                """
                INSERT INTO usuarios(nombre, usuario, clave, rol, comite_id)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (usuario) DO NOTHING
                """,
                ("Operador RAP", "operador", "operador123", "OPERADOR", default_comite_id),
            )

            if default_comite_id is not None:
                cur.execute(
                    "UPDATE usuarios SET comite_id=%s WHERE rol='OPERADOR' AND comite_id IS NULL",
                    (default_comite_id,),
                )

        conn.commit()
    finally:
        conn.close()
