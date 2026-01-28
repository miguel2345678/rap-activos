from db import get_conn


def login(usuario: str, clave: str):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    u.id, u.nombre, u.usuario, u.rol, u.activo,
                    u.comite_id,
                    c.nombre AS comite_nombre
                FROM usuarios u
                LEFT JOIN comites c ON c.id = u.comite_id
                WHERE u.usuario=%s AND u.clave=%s AND u.activo = TRUE
                """,
                (usuario, clave),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def crear_usuario_admin(nombre: str, usuario: str, clave: str, rol: str, comite_id):
    """
    Solo lo usa el ADMIN desde la pantalla Usuarios.
    - usuario debe ser único
    - OPERADOR debe tener comite_id
    - ADMIN puede tener comite_id NULL (ve todo)
    """
    nombre = (nombre or "").strip()
    usuario = (usuario or "").strip()
    clave = (clave or "").strip()
    rol = (rol or "").strip().upper()

    if not nombre or not usuario or not clave:
        return False, "Nombre/usuario/clave son obligatorios."

    if rol not in ("ADMIN", "OPERADOR"):
        return False, "Rol inválido."

    if rol == "OPERADOR" and comite_id is None:
        return False, "OPERADOR debe tener comité."

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # usuario único
            cur.execute("SELECT 1 FROM usuarios WHERE usuario=%s", (usuario,))
            existe = cur.fetchone()
            if existe:
                return False, "Ese usuario ya existe."

            cur.execute(
                """
                INSERT INTO usuarios(nombre, usuario, clave, rol, comite_id, activo)
                VALUES (%s,%s,%s,%s,%s, TRUE)
                """,
                (nombre, usuario, clave, rol, comite_id),
            )

        conn.commit()
        return True, "Usuario creado ✅"
    finally:
        conn.close()
