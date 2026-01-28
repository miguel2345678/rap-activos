from db import DB_PATH, get_conn

conn = get_conn()
rows = conn.execute("SELECT id, nombre FROM comites ORDER BY id").fetchall()
print("DB_PATH =", DB_PATH)
print("TOTAL COMITES =", len(rows))
for r in rows:
    print(r["id"], "-", r["nombre"])
conn.close()
