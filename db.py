import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

# Solo para compatibilidad (tu ver_db.py imprime DB_PATH)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# REFERENCIA VISUAL (no se usa para conectar)
DB_PATH = os.getenv("DATABASE_PUBLIC_URL", "manual-postgres")


def _clean_url(url: str) -> str:
    """
    Limpia saltos de línea/espacios invisibles que Railway/Copy-Paste mete a veces.
    """
    if not url:
        return ""
    return url.strip().replace("\n", "").replace("\r", "")


def get_conn():
    """
    MODO MANUAL ESTABLE (Railway):
    - Usa SOLO DATABASE_PUBLIC_URL (URL pública tipo postgresql://...)
    - Si no existe, fallback local (tu PC)
    """
    sslmode = os.getenv("PGSSLMODE", "require")

    # 1) URL pública (la tuya)
    dsn = _clean_url(os.getenv("DATABASE_PUBLIC_URL", ""))
    if dsn:
        # Seguridad extra: si por error te meten un token suelto, lo detectamos
        if not dsn.startswith("postgresql://") and not dsn.startswith("postgres://"):
            raise ValueError(
                f"DATABASE_PUBLIC_URL no es una URL válida. Valor recibido: {repr(dsn)}"
            )
        return psycopg.connect(dsn, row_factory=dict_row, sslmode=sslmode)

    # 2) Fallback LOCAL (tu PC)
    local_dsn = (
        f"postgresql://{os.getenv('DB_USER','postgres')}:"
        f"{os.getenv('DB_PASSWORD','')}@"
        f"{os.getenv('DB_HOST','localhost')}:"
        f"{os.getenv('DB_PORT','5432')}/"
        f"{os.getenv('DB_NAME','rap_activos')}"
    )
    return psycopg.connect(local_dsn, row_factory=dict_row, sslmode=sslmode)


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
    En Railway NO creamos tablas desde aquí.
    Solo hacemos SEED si las tablas ya existen.
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Si aún no existen tablas, esto fallará, y está bien.
            try:
                cur.execute("SELECT COUNT(*) AS n FROM comites")
                total_comites = cur.fetchone()["n"]
            except Exception:
                return  # todavía no hay schema creado

            if total_comites == 0:
                comites = [
                    "Control interno",
                    "Direccion de planeacion",
                    "Direccion financiera",
                    "Gerencia",
                    "Secretaria general y juridica",
                    "Oficina de talento humano",
                ]
                for c in comites:
                    cur.execute(
                        "INSERT INTO comites(nombre) VALUES (%s) ON CONFLICT DO NOTHING",
                        (c,),
                    )

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

            cur.execute("SELECT id FROM comites WHERE nombre=%s", ("Control interno",))
            row = cur.fetchone()
            default_comite_id = row["id"] if row else None

            cur.execute(
                """
                INSERT INTO usuarios(nombre, usuario, clave, rol, comite_id, activo)
                VALUES (%s,%s,%s,%s,%s,TRUE)
                ON CONFLICT (usuario) DO NOTHING
                """,
                ("Admin RAP", "admin", "admin123", "ADMIN", None),
            )

            cur.execute(
                """
                INSERT INTO usuarios(nombre, usuario, clave, rol, comite_id, activo)
                VALUES (%s,%s,%s,%s,%s,TRUE)
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
