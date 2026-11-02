import sqlite3
db = sqlite3.connect("data/bot.db")
print("chat_log private 2d", db.execute("SELECT COUNT(*) FROM chat_log WHERE chat_type='private' AND created >= ?", (__import__('time').time()-172800,)).fetchone()[0])
print("sessions p", db.execute("SELECT COUNT(*) FROM sessions WHERE key LIKE 'p%'").fetchone()[0])
print("messages p", db.execute("SELECT COUNT(*) FROM messages WHERE session_key LIKE 'p%'").fetchone()[0])
for row in db.execute("SELECT session_key, COUNT(*) FROM messages WHERE session_key LIKE 'p%' GROUP BY session_key"):
    print(row)
