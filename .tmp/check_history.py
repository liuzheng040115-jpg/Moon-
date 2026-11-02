import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")

con = sqlite3.connect(r"E:\qqbot\data\bot.db")
cur = con.cursor()

rows = cur.execute(
    "SELECT id, created, role, content FROM messages WHERE session_key='p1450520453' ORDER BY id DESC LIMIT 30"
).fetchall()[::-1]

print(f"私聊消息总数（库里保留）：{cur.execute(chr(83) + 'ELECT COUNT(*) FROM messages').fetchone()[0]}")
print(f"本次取到：{len(rows)} 条\n")
for mid, created, role, content in rows:
    who = "她" if role == "assistant" else "他"
    text = (content or "").replace("\n", " / ")[:70]
    print(f"{mid:4d} {who}: {text}")

con.close()
