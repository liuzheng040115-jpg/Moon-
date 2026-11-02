import sqlite3

con = sqlite3.connect(r"E:\qqbot\data\bot.db")
cur = con.cursor()
cur.execute(
    "SELECT created, is_bot, content FROM chat_log "
    "WHERE chat_id = '1450520453' ORDER BY id DESC LIMIT 120"
)
rows = cur.fetchall()[::-1]

for created, is_bot, content in rows:
    who = "我" if is_bot else "他"
    text = (content or "").replace("\n", " | ")
    print(f"[{created}] {who}: {text}")
