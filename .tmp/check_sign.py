import sqlite3, time
db = sqlite3.connect("data/bot.db")
for row in db.execute("SELECT chat_type, chat_id, nickname, content, is_bot, created FROM chat_log WHERE content LIKE '%签名%' OR content LIKE '%longNick%' ORDER BY id DESC LIMIT 40"):
    print(time.strftime("%m-%d %H:%M", time.localtime(row[5])), row[0], row[1], "BOT" if row[4] else "USER", row[2], repr(row[3]))
