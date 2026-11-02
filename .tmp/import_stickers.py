import hashlib
import sqlite3
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

now = time.time()

DB = r"E:\qqbot\data\bot.db"
STICKER_DIR = Path(r"E:\qqbot\data\stickers")

# 两张图是主人从 QQ 发过来的，直接读 OneBot 落盘的媒体文件
ITEMS = [
    {
        "src": r"C:\Users\86182\.dsh\media\onebot\media_1793554809524_ccff9bc0.jpg",
        "description": "蓝色长发鲸鱼娘，深蓝白女仆装，戴墨镜端着一杯白瓷茶杯，姿态从容，下方大字「已阅，退下吧」。透着审视、打发人的冷淡感。",
        "usage_note": "懒得接话、对方说了废话、或要摆出「我看过了你可以滚了」的姿态时用",
        "context": "主人发来的表情包，指定经常用",
    },
    {
        "src": r"C:\Users\86182\.dsh\media\onebot\media_1793554809746_9f6f7425.jpg",
        "description": "同一个鲸鱼娘趴在笔记本电脑前，眼睛转成圈、流汗、头顶冒烟，电脑屏幕上红色警告三角，下方大字「CPU 烧干了，晕鱼」。晕头转向、被搞崩溃的样子。",
        "usage_note": "被问题绕晕、连续报错、脑子不够用、或者自嘲被折腾惨了的时候用",
        "context": "主人发来的表情包，指定经常用",
    },
]

con = sqlite3.connect(DB)
cur = con.cursor()

for item in ITEMS:
    src = Path(item["src"])
    if not src.exists():
        print(f"跳过（文件不存在）：{src}")
        continue
    data = src.read_bytes()
    digest = hashlib.sha256(data).hexdigest()

    cur.execute("SELECT id FROM saved_stickers WHERE image_hash = ?", (digest,))
    hit = cur.fetchone()
    if hit:
        print(f"已存在 #{hit[0]}：{item['description'][:20]}")
        continue

    STICKER_DIR.mkdir(parents=True, exist_ok=True)
    dst = STICKER_DIR / f"{digest[:16]}.jpg"
    dst.write_bytes(data)

    cur.execute(
        "INSERT INTO saved_stickers "
        "(file_path, description, usage_note, source_chat, source_user, context, image_hash, created, last_used, use_count) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
        (
            str(dst),
            item["description"],
            item["usage_note"],
            "private:1450520453",
            "明天阵雨转晴",
            item["context"],
            digest,
            now,
            now,
        ),
    )
    print(f"已存入 #{cur.lastrowid}：{dst.name}")

con.commit()

print("\n=== 当前收藏 ===")
for row in con.execute(
    "SELECT id, description, use_count FROM saved_stickers ORDER BY id"
):
    print(f"#{row[0]} 用过{row[2]}次  {row[1][:45]}")

con.close()
