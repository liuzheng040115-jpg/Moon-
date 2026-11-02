import sqlite3, time
db=sqlite3.connect("data/bot.db")
for row in db.execute("SELECT nickname, content, is_bot, created FROM chat_log WHERE chat_type='private' AND chat_id=1450520453 ORDER BY id DESC LIMIT 30"):
    print(time.strftime("%H:%M:%S", time.localtime(row[3])), "BOT" if row[2] else "USER", row[0], repr(row[1]))
