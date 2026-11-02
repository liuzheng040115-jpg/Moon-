import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")

con = sqlite3.connect(r"E:\qqbot\data\bot.db")

print("=== chat_log 里所有含「倒杯水」或「水」的记录 ===")
for row in con.execute(
    "SELECT id, created, is_bot, content FROM chat_log "
    "WHERE chat_id='1450520453' AND content LIKE '%水%' ORDER BY id DESC LIMIT 10"
):
    print(row)

print("\n=== messages 里最近 12 条原文（不截断） ===")
for mid, role, content in con.execute(
    "SELECT id, role, content FROM messages WHERE session_key='p1450520453' "
    "ORDER BY id DESC LIMIT 12"
).fetchall()[::-1]:
    who = "她" if role == "assistant" else "他"
    print(f"{mid} {who}: {content!r}")

con.close()
