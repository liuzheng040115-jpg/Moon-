import sqlite3, time
db=sqlite3.connect("data/bot.db")
rows=list(db.execute("SELECT content, is_bot, created FROM chat_log WHERE chat_type='private' AND chat_id=1450520453 ORDER BY id DESC LIMIT 16"))
for r in reversed(rows):
    print(time.strftime("%H:%M:%S", time.localtime(r[2])), "BOT" if r[1] else "USER", repr(r[0]))
