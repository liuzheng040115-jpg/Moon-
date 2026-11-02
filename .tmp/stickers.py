import sqlite3
db = sqlite3.connect("data/bot.db")
for row in db.execute("SELECT id, description, usage_note, source_user FROM saved_stickers ORDER BY id"):
    print(row)
