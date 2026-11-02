import sqlite3
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

con = sqlite3.connect(r"E:\qqbot\data\bot.db")

print("=== chat_log 按类型统计 ===")
for row in con.execute(
    "SELECT chat_type, chat_id, COUNT(*), MAX(created) FROM chat_log "
    "GROUP BY chat_type, chat_id ORDER BY COUNT(*) DESC"
):
    ctype, cid, n, latest = row
    when = time.strftime("%m-%d %H:%M", time.localtime(latest))
    print(f"{ctype:8s} {str(cid):15s} {n:5d} 条  最后 {when}")

print("\n=== group_messages 统计 ===")
for row in con.execute(
    "SELECT group_id, COUNT(*), MAX(created) FROM group_messages GROUP BY group_id"
):
    gid, n, latest = row
    when = time.strftime("%m-%d %H:%M", time.localtime(latest))
    print(f"群 {gid}: {n} 条  最后 {when}")

print("\n现在:", time.strftime("%m-%d %H:%M"))
con.close()
