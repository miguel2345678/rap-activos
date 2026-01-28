import psycopg2
import psycopg2.extras
from pathlib import Path

# =========================
# CONFIG POSTGRES (ajusta contraseña)
# =========================
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "rap_activos"
DB_USER = "postgres"
DB_PASSWORD = "postgres12345"

# Por compatibilidad (tu ver_db.py imprime DB_PATH)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = f"postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor,
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
            # Si el INSERT tiene RETURNING id, obtenemos el id
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
    En Postgres NO vamos a leer schema.sql (porque el tuyo es SQLite).
    Aquí asumimos que YA creaste tablas en pgAdmin.
    Solo hacemos el SEED (comités y admin/operador) si no existen.
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # =========================
            # 1) Seed comités
            # =========================
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
                    cur.execute("INSERT INTO comites(nombre) VALUES (%s) ON CONFLICT DO NOTHING", (c,))

            # =========================
            # 2) Seed catálogos (opcional)
            # =========================
            categorias = ["Equipos TI", "Mobiliario", "Herramientas"]
            ubicaciones = ["Sede Principal", "Administración", "Planeación"]
            responsables = ["Sin asignar", "Administrador RAP"]

            for c in categorias:
                cur.execute("INSERT INTO categorias(nombre) VALUES (%s) ON CONFLICT DO NOTHING", (c,))
            for u in ubicaciones:
                cur.execute("INSERT INTO ubicaciones(nombre) VALUES (%s) ON CONFLICT DO NOTHING", (u,))
            for r in responsables:
                cur.execute("INSERT INTO responsables(nombre) VALUES (%s) ON CONFLICT DO NOTHING", (r,))

            # =========================
            # 3) Admin + Operador demo
            # =========================
            cur.execute("SELECT id FROM comites WHERE nombre=%s", ("Control interno",))
            row = cur.fetchone()
            default_comite_id = row["id"] if row else None

            # Admin
            cur.execute(
                """
                INSERT INTO usuarios(nombre, usuario, clave, rol, comite_id)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (usuario) DO NOTHING
                """,
                ("Admin RAP", "admin", "admin123", "ADMIN", None),
            )

            # Operador demo
            cur.execute(
                """
                INSERT INTO usuarios(nombre, usuario, clave, rol, comite_id)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (usuario) DO NOTHING
                """,
                ("Operador RAP", "operador", "operador123", "OPERADOR", default_comite_id),
            )

            # Reparar operadores viejos sin comité
            if default_comite_id is not None:
                cur.execute(
                    "UPDATE usuarios SET comite_id=%s WHERE rol='OPERADOR' AND comite_id IS NULL",
                    (default_comite_id,),
                )

        conn.commit()
    finally:
        conn.close()
