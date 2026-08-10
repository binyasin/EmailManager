import sqlite3
db = sqlite3.connect(r"C:\Users\DELL LATITUDE 5520\.openclaw\workspace\skills\smart-email\data\email.db")
tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("TABLES:")
for t in tables:
    print(f"  -> '{t[0]}'")
    cols = db.execute(f"PRAGMA table_info('{t[0]}')").fetchall()
    for i, c in enumerate(cols):
        print(f"     [{i}] {c[1]} ({c[2]})")
    if 'email' in [c[1] for c in cols]:
        rows = db.execute(f"SELECT * FROM '{t[0]}' WHERE email LIKE '%stellar%'").fetchall()
        for r in rows:
            print(f"     MATCH: {r}")
db.close()
