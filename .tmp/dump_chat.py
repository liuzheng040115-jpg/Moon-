import sqlite3, time
db = sqlite3.connect("data/bot.db")
def ts(t):
    return time.strftime("%m-%d %H:%M", time.localtime(t))
print("=== chat_log 最近 120 条 ===")
rows = list(db.execute("SELECT chat_type, chat_id, user_id, nickname, content, is_bot, created FROM chat_log ORDER BY id DESC LIMIT 120"))
for r in reversed(rows):
    ctype, cid, uid, nick, content, is_bot, created = r
    who = "BOT" if is_bot else "USER"
    print(f"{ts(created)} [{ctype}:{cid}] {who} {nick}({uid}): {content!r}")
print()
print("=== assistant messages 最近 80 条 ===")
rows = list(db.execute("SELECT session_key, role, content, created FROM messages WHERE role='assistant' ORDER BY id DESC LIMIT 80"))
for r in reversed(rows):
    print(f"{ts(r[3])} {r[0]}: {r[2]!r}")
