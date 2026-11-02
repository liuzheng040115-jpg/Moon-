import sqlite3, re, collections, statistics, time
db = sqlite3.connect("data/bot.db")
bots = [r[0] for r in db.execute("SELECT content FROM messages WHERE role='assistant' ORDER BY id DESC LIMIT 200")]
humans = [r[0] for r in db.execute("SELECT content FROM chat_log WHERE is_bot=0 AND content NOT LIKE '[图片]%' AND content NOT LIKE '[表情%' AND content NOT LIKE '[对方发来%' ORDER BY id DESC LIMIT 300")]

def stats(name, rows):
    rows = [x for x in rows if x]
    print(f"--- {name}: {len(rows)} 条 ---")
    print("平均字数", round(statistics.mean(len(x) for x in rows), 1), "中位", statistics.median(len(x) for x in rows))
    ends = collections.Counter()
    for x in rows:
        ends["。" if x.endswith("。") else "？" if x.endswith("？") else "！" if x.endswith("！") else "…" if x.endswith(("…","...")) else "无"] += 1
    print("结尾", dict(ends))
    print("含逗号", sum(1 for x in rows if "，" in x), "含句号", sum(1 for x in rows if "。" in x))
    print("开头4字 top", collections.Counter(x[:4] for x in rows).most_common(12))
    print("高频词", collections.Counter(w for x in rows for w in re.findall(r'[\u4e00-\u9fff]{2,4}', x)).most_common(25))
    print()
stats("BOT 最近200", bots)
stats("人类最近300", humans)
