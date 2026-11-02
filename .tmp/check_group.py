import sqlite3, os
p = ".tmp/selftest.db"
print("exists", os.path.exists(p), os.path.getsize(p) if os.path.exists(p) else 0)
db = sqlite3.connect(p)
for t in ("group_messages","messages","user_facts"):
    try:
        print(t, db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
    except Exception as e:
        print(t, e)
