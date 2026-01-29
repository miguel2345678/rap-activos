import os
from pathlib import Path

import psycopg
from  psycopg.rows import dict_row

# Por compatibilidad con ver_db.py (solo informativo)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = os.getenv("DATABASE_URL", "postgresql://localhost:5432/rap_activos")


def get_conn():
    dsn = os.getenv("DATABASE_URL")
    print("DEBUG DATABASE_URL:", repr(dsn)) 
    if not dsn:
        # Fallback LOCAL (tu PC)
        dsn = (
            f"postgresql://{os.getenv('DB_USER','postgres')}:"
            f"{os.getenv('DB_PASSWORD','')}@"
            f"{os.getenv('DB_HOST','localhost')}:"
            f"{os.getenv('DB_PORT','5432')}/"
            f"{os.getenv('DB_NAME','rap_activos')}"
        )

    # En Railway normalmente se requiere TLS/SSL.
    # Con psycopg v3, sslmode va como parámetro.
    sslmode = os.getenv("PGSSLMODE", "require")

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
    En Railway NO uses schema.sql SQLite.
    Aquí solo hacemos seed si las tablas YA existen.
    (Luego te paso el SQL para crear tablas en Railway si aún no están.)
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Seed comités si está vacío
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

            # Seed catálogos
            categorias = ["Equipos TI", "Mobiliario", "Herramientas"]
            ubicaciones = ["Sede Principal", "Administración", "Planeación"]
            responsables = ["Sin asignar", "Administrador RAP"]

            for c in categorias:
                cur.execute(
                    "INSERT INTO categorias(nombre) VALUES (%s) ON CONFLICT DO NOTHING",
                    (c,),
                )
            for u in ubicaciones:
                cur.execute(
                    "INSERT INTO ubicaciones(nombre) VALUES (%s) ON CONFLICT DO NOTHING",
                    (u,),
                )
            for r in responsables:
                cur.execute(
                    "INSERT INTO responsables(nombre) VALUES (%s) ON CONFLICT DO NOTHING",
                    (r,),
                )

            # Admin + Operador demo
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
