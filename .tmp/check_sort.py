import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")

con = sqlite3.connect(r"E:\qqbot\data\bot.db")
rows = con.execute(
    "SELECT id, description, usage_note FROM saved_stickers ORDER BY created DESC LIMIT 20"
).fetchall()

rows = sorted(rows, key=lambda r: 0 if "【常用】" in str(r[2] or "") else 1)

print("=== 排序后的清单（模拟 prompt）===")
for sticker_id, description, usage_note in rows:
    line = f"#{sticker_id} {str(description)[:40]}"
    if usage_note:
        line += f"（适合：{str(usage_note)[:30]}）"
    print(line)

row = con.execute(
    "SELECT COUNT(*) FROM saved_stickers WHERE usage_note LIKE '%【常用】%'"
).fetchone()
print(f"\n【常用】标记数量：{row[0]}")
con.close()
