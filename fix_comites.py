import sqlite3
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "rap_activos.db"

OFICIALES = [
    "Control interno",
    "Direccion de planeacion",
    "Direccion financiera",
    "Gerencia",
    "Secretaria general y juridica",
    "Oficina de talento humano",
]

def norm(s: str) -> str:
    s = s.strip().lower()
    s = "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )
    s = " ".join(s.split())
    return s

def main():
    print("DB_PATH =", DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1) Asegurar que existan EXACTAMENTE los 6 oficiales (insert si faltan)
    for n in OFICIALES:
        cur.execute("INSERT OR IGNORE INTO comites(nombre) VALUES (?)", (n,))
    conn.commit()

    # 2) Leer todos los comites actuales
    cur.execute("SELECT id, nombre FROM comites")
    rows = cur.fetchall()

    canon = {norm(x): x for x in OFICIALES}

    # 3) Elegir el "ID bueno" para cada comité (el menor id por cada nombre normalizado)
    id_bueno = {}
    for r in rows:
        k = norm(r["nombre"])
        if k in canon:
            if k not in id_bueno or r["id"] < id_bueno[k]:
                id_bueno[k] = r["id"]

    # 4) Mover referencias (activos/usuarios) de IDs duplicados hacia el ID bueno
    for r in rows:
        k = norm(r["nombre"])
        if k in id_bueno:
            bueno = id_bueno[k]
            if r["id"] != bueno:
                cur.execute("UPDATE activos SET comite_id=? WHERE comite_id=?", (bueno, r["id"]))
                cur.execute("UPDATE usuarios SET comite_id=? WHERE comite_id=?", (bueno, r["id"]))
    conn.commit()

    # 5) Borrar duplicados
    cur.execute("SELECT id, nombre FROM comites")
    rows2 = cur.fetchall()

    borrar = []
    for r in rows2:
        k = norm(r["nombre"])
        if k in id_bueno and r["id"] != id_bueno[k]:
            borrar.append(r["id"])

    if borrar:
        placeholders = ",".join(["?"] * len(borrar))
        cur.execute(f"DELETE FROM comites WHERE id IN ({placeholders})", borrar)
        conn.commit()

    # 6) Mostrar cómo quedó
    cur.execute("SELECT id, nombre FROM comites ORDER BY nombre")
    final = cur.fetchall()

    print("TOTAL COMITES =", len(final))
    for r in final:
        print(r["id"], "-", r["nombre"])

    conn.close()
    print("✅ Listo. Ya deben quedar solo 6.")

if __name__ == "__main__":
    main()
