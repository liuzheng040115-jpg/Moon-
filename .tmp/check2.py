import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")

con = sqlite3.connect(r"E:\qqbot\data\bot.db")
rows = con.execute(
    "SELECT id, role, content FROM messages WHERE session_key='p1450520453' "
    "ORDER BY id DESC LIMIT 40"
).fetchall()[::-1]

for mid, role, content in rows:
    who = "她" if role == "assistant" else "他"
    text = (content or "").replace("\n", " / ")
    print(f"{mid} {who}: {text[:90]}")

con.close()
