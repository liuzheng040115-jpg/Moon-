import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")

con = sqlite3.connect(r"E:\qqbot\data\bot.db")
cur = con.cursor()

rows = cur.execute(
    "SELECT created, is_bot, content FROM chat_log "
    "WHERE chat_id = '1450520453' ORDER BY id DESC LIMIT 90"
).fetchall()[::-1]

for created, is_bot, content in rows:
    who = "我" if is_bot else "他"
    text = (content or "").replace("\n", " / ")
    print(f"{who}: {text}")

con.close()
