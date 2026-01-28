import streamlit as st
import pandas as pd

from db import init_db, qone, qall, exec_sql
from auth import login, crear_usuario_admin

st.set_page_config(page_title="RAP Amazonía - Gestión de Activos", layout="wide")


def set_title(text: str):
    # Un solo “slot” de título para toda la app
    if "_title_slot" not in st.session_state:
        st.session_state["_title_slot"] = st.empty()
    st.session_state["_title_slot"].title(text)


# ======================
# Helpers de permisos
# ======================
def es_admin():
    return st.session_state.get("user") and st.session_state["user"]["rol"] == "ADMIN"


def comite_scope():
    """
    Retorna (where_sql, params, label)
    - ADMIN: usa st.session_state["vista_comite_id"] (0 = Todos)
    - OPERADOR: fijo a su comité
    """
    user = st.session_state["user"]
    comites = qall("SELECT id, nombre FROM comites ORDER BY nombre")
    id2name = {c["id"]: c["nombre"] for c in comites}

    if user["rol"] == "ADMIN":
        cid = st.session_state.get("vista_comite_id", 0)
        if cid == 0:
            return "", (), "Todos"
        return " WHERE a.comite_id=%s ", (cid,), id2name.get(cid, "Desconocido")

    # OPERADOR
    cid = user["comite_id"]
    nombre = user.get("comite_nombre") or id2name.get(cid, "Mi comité")
    return " WHERE a.comite_id=%s ", (cid,), nombre


# ======================
# Login UI
# ======================
def pantalla_login():
    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Clave", type="password")
        ok = st.form_submit_button("Ingresar")

    if ok:
        user = login(u, p)
        if user:
            st.session_state["user"] = user
            st.success("Bienvenido ✅")
            st.rerun()
        else:
            st.error("Usuario/clave incorrectos o inactivo.")


# ======================
# Dashboard
# ======================
def dashboard():
    user = st.session_state["user"]

    # ✅ ADMIN: vista global; OPERADOR: su comité (y etiqueta correcta)
    if user["rol"] == "ADMIN":
        where, params, label = "", (), "Todos"
    else:
        where, params, label = comite_scope()

    st.caption(f"Vista: **{label}**")

    df = pd.DataFrame(
        qall(
            f"""
            SELECT estado, COUNT(*) as total
            FROM activos a
            {where}
            GROUP BY estado
            """,
            params,
        )
    )

    total = int(df["total"].sum()) if not df.empty else 0
    activos = int(df[df["estado"] == "ACTIVO"]["total"].sum()) if not df.empty else 0
    rep = int(df[df["estado"] == "REPARACION"]["total"].sum()) if not df.empty else 0
    baja = int(df[df["estado"] == "BAJA"]["total"].sum()) if not df.empty else 0

    a, b, c, d = st.columns(4)
    a.metric("Total", total)
    b.metric("ACTIVO", activos)
    c.metric("REPARACIÓN", rep)
    d.metric("BAJA", baja)

    st.markdown("### ⚠️ Alertas")

    sin_resp = qone(
        f"""
        SELECT COUNT(*) as n FROM activos a
        {where} {" AND " if where else " WHERE "}
        a.responsable_id IS NULL
        """,
        params,
    )["n"]

    sin_ubi = qone(
        f"""
        SELECT COUNT(*) as n FROM activos a
        {where} {" AND " if where else " WHERE "}
        a.ubicacion_id IS NULL
        """,
        params,
    )["n"]

    en_rep = qone(
        f"""
        SELECT COUNT(*) as n FROM activos a
        {where} {" AND " if where else " WHERE "}
        a.estado='REPARACION'
        """,
        params,
    )["n"]

    sin_cat = qone(
        f"""
        SELECT COUNT(*) as n FROM activos a
        {where} {" AND " if where else " WHERE "}
        a.categoria_id IS NULL
        """,
        params,
    )["n"]

    c1, c2 = st.columns(2)
    c1.warning(f"Activos sin responsable: {sin_resp}")
    c2.warning(f"Activos sin ubicación: {sin_ubi}")

    c3, c4 = st.columns(2)
    c3.warning(f"Activos en REPARACIÓN: {en_rep}")
    c4.warning(f"Activos sin categoría: {sin_cat}")


# ======================
# Registrar activo
# ======================
def registrar_activo():
    user = st.session_state["user"]

    # Comité del activo
    if user["rol"] == "ADMIN":
        comites = qall("SELECT id, nombre FROM comites ORDER BY nombre")
        comite_nombre = st.selectbox(
            "Comité del activo",
            [c["nombre"] for c in comites],
            key="ra_comite_nombre",
        )
        comite_id = next(c["id"] for c in comites if c["nombre"] == comite_nombre)
    else:
        comite_id = user["comite_id"]
        st.info(f"Este activo se registrará en tu comité: **{user.get('comite_nombre','(sin nombre)')}**")

    with st.form("reg_activo", clear_on_submit=True):
        codigo = st.text_input("Código (opcional)", key="ra_codigo")
        nombre = st.text_input("Nombre del activo", key="ra_nombre")
        descripcion = st.text_area("Descripción", height=80, key="ra_descripcion")

        estado = st.selectbox("Estado", ["ACTIVO", "REPARACION", "BAJA"], key="ra_estado")

        # ✍️ CAMPOS LIBRES (ya no selectivos)
        categoria_txt = st.text_input("Categoría (opcional)", key="ra_categoria_txt")
        ubicacion_txt = st.text_input("Ubicación (opcional)", key="ra_ubicacion_txt")
        responsable_txt = st.text_input("Responsable (opcional)", key="ra_responsable_txt")

        ok = st.form_submit_button("Guardar")

    if ok:
        if not nombre.strip():
            st.error("El nombre del activo es obligatorio.")
            return

        codigo_norm = (codigo or "").strip()
        if codigo_norm == "":
            codigo_norm = None

        # ⚠️ Por ahora NO usamos IDs (empresa no ha definido catálogos)
        try:
            exec_sql(
                """
                INSERT INTO activos(
                    codigo, nombre, descripcion, estado,
                    fecha_registro,
                    categoria_id, ubicacion_id, responsable_id, comite_id
                )
                VALUES (%s,%s,%s,%s, NOW(), NULL, NULL, NULL, %s)
                """,
                (
                    codigo_norm,
                    nombre.strip(),
                    descripcion.strip(),
                    estado,
                    comite_id,
                ),
            )
            st.success("Activo registrado ✅")

        except Exception as e:
            msg = str(e).lower()
            # Postgres suele decir: duplicate key value violates unique constraint
            if "unique" in msg and "codigo" in msg:
                st.error("Ese código ya existe. Usa otro código o déjalo vacío.")
            else:
                st.error(f"Error al guardar: {e}")


# ======================
# Listado de activos
# ======================
def listado_activos():
    st.subheader("📋 Listado de activos")

    where, params, label = comite_scope()
    st.caption(f"Vista: **{label}**")

    q = st.text_input("Buscar (código o nombre)")
    extra_where = ""
    extra_params = ()

    if q.strip():
        extra_where = (" AND " if where else " WHERE ") + "(a.codigo LIKE %s OR a.nombre LIKE %s)"
        like = f"%{q.strip()}%"
        extra_params = (like, like)

    rows = qall(
        f"""
        SELECT
          a.id, a.codigo, a.nombre, a.estado, a.fecha_registro,
          c.nombre as categoria,
          u.nombre as ubicacion,
          r.nombre as responsable,
          co.nombre as comite
        FROM activos a
        LEFT JOIN categorias c ON c.id = a.categoria_id
        LEFT JOIN ubicaciones u ON u.id = a.ubicacion_id
        LEFT JOIN responsables r ON r.id = a.responsable_id
        JOIN comites co ON co.id = a.comite_id
        {where}
        {extra_where}
        ORDER BY a.id DESC
        """,
        params + extra_params,
    )

    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No hay activos para mostrar.")
        return

    # ✅ ADMIN: tabla bonita + eliminar por fila (checkbox)
    if es_admin():
        view = df.copy()
        if "Eliminar" not in view.columns:
            view["Eliminar"] = False

        edited = st.data_editor(
            view,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Eliminar": st.column_config.CheckboxColumn("🗑️ Eliminar", help="Marca para eliminar"),
                "id": st.column_config.NumberColumn("ID", width="small"),
                "codigo": st.column_config.TextColumn("Código", width="medium"),
                "nombre": st.column_config.TextColumn("Nombre", width="large"),
                "estado": st.column_config.TextColumn("Estado", width="small"),
                "fecha_registro": st.column_config.TextColumn("Registro", width="medium"),
                "comite": st.column_config.TextColumn("Comité", width="medium"),
            },
            disabled=[c for c in view.columns if c != "Eliminar"],
            key="activos_editor",
        )

        ids = edited.loc[edited["Eliminar"] == True, "id"].tolist()

        if ids:
            st.warning(
                f"Vas a eliminar definitivamente {len(ids)} activo(s): {', '.join(map(str, ids))}. "
                "Esto no se puede deshacer."
            )
            c1, c2 = st.columns(2)
            if c1.button("✅ Eliminar seleccionados", key="btn_del_sel"):
                try:
                    for aid in ids:
                        # si hay movimientos, borrarlos antes (por orden y por seguridad)
                        exec_sql("DELETE FROM movimientos WHERE activo_id=%s", (int(aid),))
                        exec_sql("DELETE FROM activos WHERE id=%s", (int(aid),))
                    st.success("Eliminados ✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo eliminar: {e}")

            if c2.button("❌ Cancelar", key="btn_del_cancel"):
                st.rerun()

    # ✅ OPERADOR: tabla normal (bonita)
    else:
        st.dataframe(df, use_container_width=True)

    # ⚠️ NO TOCAR: Dar de baja (rápido)
    st.divider()
    st.markdown("### 🧾 Dar de baja (rápido)")
    aid = st.number_input("ID del activo", min_value=1, step=1, key="baja_activo_id")

    if st.button("Marcar como BAJA", key="btn_baja"):
        exec_sql("UPDATE activos SET estado='BAJA' WHERE id=%s", (int(aid),))

        # ✅ Tu schema real tiene: (activo_id, fecha, tipo, detalle)
        exec_sql(
            """
            INSERT INTO movimientos(activo_id, tipo, detalle, fecha)
            VALUES (%s, %s, %s, NOW())
            """,
            (
                int(aid),
                "CAMBIO_ESTADO",
                "Marcado como BAJA desde listado",
            ),
        )

        st.success("Listo ✅")
        st.rerun()


# ======================
# Admin: Usuarios
# ======================
def admin_usuarios():
    user = st.session_state["user"]

    st.subheader("👥 Usuarios")

    # ======================
    # Crear usuario (igual que antes)
    # ======================
    comites = qall("SELECT id, nombre FROM comites ORDER BY nombre")

    with st.form("crear_usuario"):
        nombre = st.text_input("Nombre")
        usuario = st.text_input("Usuario (login)")
        clave = st.text_input("Clave", type="password")

        rol = st.selectbox("Rol", ["OPERADOR", "ADMIN"])

        if rol == "ADMIN":
            comite_id = None
            st.info("Los usuarios ADMIN pueden ver todos los comités.")
        else:
            comite_nombre = st.selectbox("Comité del usuario", [c["nombre"] for c in comites])
            comite_id = next(c["id"] for c in comites if c["nombre"] == comite_nombre)

        ok = st.form_submit_button("Crear usuario")

    if ok:
        if not nombre.strip() or not usuario.strip() or not clave.strip():
            st.error("Nombre, usuario y clave son obligatorios.")
        else:
            success, msg = crear_usuario_admin(
                nombre.strip(),
                usuario.strip(),
                clave.strip(),
                rol,
                comite_id,
            )
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    st.divider()
    st.markdown("### 📜 Usuarios existentes")

    rows = qall(
        """
        SELECT
            u.id,
            u.nombre,
            u.usuario,
            u.rol,
            u.activo,
            c.nombre AS comite
        FROM usuarios u
        LEFT JOIN comites c ON c.id = u.comite_id
        ORDER BY u.id DESC
        """
    )

    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No hay usuarios registrados.")
        return

    # ======================
    # ADMIN: tabla bonita + eliminar
    # ======================
    if es_admin():
        view = df.copy()
        view["Eliminar"] = False

        edited = st.data_editor(
            view,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Eliminar": st.column_config.CheckboxColumn("🗑️ Eliminar"),
                "id": st.column_config.NumberColumn("ID", width="small"),
                "nombre": st.column_config.TextColumn("Nombre"),
                "usuario": st.column_config.TextColumn("Usuario"),
                "rol": st.column_config.TextColumn("Rol"),
                "activo": st.column_config.NumberColumn("Activo"),
                "comite": st.column_config.TextColumn("Comité"),
            },
            disabled=[c for c in view.columns if c != "Eliminar"],
            key="usuarios_editor",
        )

        ids = edited.loc[edited["Eliminar"] == True, "id"].tolist()

        # 🔒 reglas de seguridad
        ids_seguro = []
        bloqueados = []

        for uid in ids:
            row = df[df["id"] == uid].iloc[0]

            if int(uid) == int(user["id"]):
                bloqueados.append(f"{row['usuario']} (sesión actual)")
            elif row["rol"] == "ADMIN":
                bloqueados.append(f"{row['usuario']} (ADMIN)")
            else:
                ids_seguro.append(uid)

        if bloqueados:
            st.warning("No se pueden eliminar estos usuarios:\n- " + "\n- ".join(bloqueados))

        if ids_seguro:
            st.warning(
                f"Vas a eliminar {len(ids_seguro)} usuario(s): {', '.join(map(str, ids_seguro))}. "
                "Esto no se puede deshacer."
            )

            c1, c2 = st.columns(2)
            if c1.button("✅ Eliminar seleccionados"):
                try:
                    for uid in ids_seguro:
                        exec_sql("DELETE FROM usuarios WHERE id=%s", (int(uid),))
                    st.success("Usuarios eliminados ✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo eliminar: {e}")

            if c2.button("❌ Cancelar"):
                st.rerun()

    # ======================
    # OPERADOR: solo ver
    # ======================
    else:
        st.dataframe(df, use_container_width=True)


# ======================
# App principal
# ======================
def main_app():
    user = st.session_state["user"]

    st.sidebar.title("Menú")
    st.sidebar.caption(f"👤 {user['nombre']} | Rol: {user['rol']}")
    if user.get("comite_nombre"):
        st.sidebar.caption(f"🏛️ Comité: {user['comite_nombre']}")

    opciones = ["Panel", "Registrar activo", "Listado de activos", "Usuarios"]
    menu = st.sidebar.radio("Ir a:", opciones, index=0)

    # ✅ Mostrar filtro de comité SOLO en "Listado de activos" (solo ADMIN)
    if user["rol"] == "ADMIN" and menu == "Listado de activos":
        comites = qall("SELECT id, nombre FROM comites ORDER BY nombre")
        id2name = {c["id"]: c["nombre"] for c in comites}

        # migración por si quedó algo viejo
        if "vista_comite_id" not in st.session_state:
            viejo = st.session_state.get("vista_comite")
            if viejo and viejo != "Todos":
                st.session_state["vista_comite_id"] = next(
                    (c["id"] for c in comites if c["nombre"] == viejo), 0
                )
            else:
                st.session_state["vista_comite_id"] = 0  # 0 = Todos

        st.sidebar.selectbox(
            "🏛️ Comité (vista)",
            [0] + [c["id"] for c in comites],
            key="vista_comite_id",
            format_func=lambda cid: "Todos" if cid == 0 else id2name.get(cid, "Desconocido"),
        )
    else:
        # ✅ Fuera del listado, fijamos la vista a "Todos" para ADMIN
        if user["rol"] == "ADMIN":
            st.session_state["vista_comite_id"] = 0

    if st.sidebar.button("Cerrar sesión"):
        st.session_state.pop("user", None)
        st.rerun()

    TITULOS = {
        "Panel": "📊 Panel de control",
        "Registrar activo": "📝 Registrar activo",
        "Listado de activos": "📋 Listado de activos",
        "Usuarios": "👥 Usuarios",
    }
    set_title(TITULOS.get(menu, "RAP Amazonía - Gestión de Activos"))

    if menu == "Panel":
        dashboard()
    elif menu == "Registrar activo":
        registrar_activo()
    elif menu == "Listado de activos":
        listado_activos()
    else:
        admin_usuarios()


def boot():
    if "db_inited" not in st.session_state:
        init_db()
        st.session_state["db_inited"] = True

    if "user" not in st.session_state or not st.session_state["user"]:
        set_title("🔐 Ingreso - Gestión de Activos (RAP Amazonía)")
        pantalla_login()
    else:
        main_app()


if __name__ == "__main__":
    boot()
