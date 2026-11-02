import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")

con = sqlite3.connect(r"E:\qqbot\data\bot.db")
cur = con.cursor()

print("=== sessions ===")
for row in cur.execute("SELECT key, updated FROM sessions"):
    print(row)

print("\n=== messages（按会话）===")
for row in cur.execute(
    "SELECT session_key, COUNT(*) FROM messages GROUP BY session_key"
):
    print(row)

print("\n=== messages 内容（最近 40 条）===")
for role, content, created in cur.execute(
    "SELECT role, content, created FROM messages ORDER BY id DESC LIMIT 40"
):
    text = (content or "").replace("\n", " | ")
    print(f"[{created}] {role}: {text[:160]}")

print("\n=== user_facts ===")
for row in cur.execute("SELECT scope, fact FROM user_facts"):
    print(row)

print("\n=== chat_log 统计 ===")
for row in cur.execute(
    "SELECT chat_type, chat_id, COUNT(*) FROM chat_log GROUP BY chat_type, chat_id"
):
    print(row)

con.close()
