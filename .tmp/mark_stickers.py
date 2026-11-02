import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")

con = sqlite3.connect(r"E:\qqbot\data\bot.db")
cur = con.cursor()

UPDATES = {
    4: "【常用】懒得接话、对方说了废话、或要摆出「我看过了你可以滚了」的姿态时用",
    5: "【常用】被问题绕晕、连续报错、脑子不够用、或自嘲被折腾惨了的时候用",
}

for sid, note in UPDATES.items():
    cur.execute(
        "UPDATE saved_stickers SET usage_note = ? WHERE id = ?", (note, sid)
    )
    print(f"#{sid} -> {note[:30]}")

con.commit()

print("\n=== 复查 ===")
for row in con.execute("SELECT id, usage_note FROM saved_stickers ORDER BY id"):
    print(f"#{row[0]}: {row[1]}")

con.close()
