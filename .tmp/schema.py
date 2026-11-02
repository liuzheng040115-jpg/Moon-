import sqlite3, json, time
db = sqlite3.connect("data/bot.db")
for row in db.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"):
    print("TABLE", row[0])
    print(row[1])
    print()
