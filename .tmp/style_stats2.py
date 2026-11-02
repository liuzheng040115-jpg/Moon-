import sqlite3, collections, statistics, re
db = sqlite3.connect("data/bot.db")
bots = [r[0] for r in db.execute("SELECT content FROM chat_log WHERE is_bot=1 AND content NOT LIKE '[表情包]%' AND content NOT LIKE '[图片]%' ORDER BY id DESC LIMIT 400")]
print("条数", len(bots))
print("平均", round(statistics.mean(len(x) for x in bots),1), "中位", statistics.median(len(x) for x in bots))
ends = collections.Counter()
for x in bots:
    ends["。" if x.endswith("。") else "？" if x.endswith("？") else "！" if x.endswith("！") else "…" if x.endswith(("…","...")) else "无"] += 1
print("结尾", dict(ends))
print("含逗号", sum(1 for x in bots if "，" in x), "/", len(bots))
print("含句号", sum(1 for x in bots if "。" in x), "/", len(bots))
print("长度分布", collections.Counter(min(len(x)//10*10, 60) for x in bots))
print("开头3字top", collections.Counter(x[:3] for x in bots).most_common(20))
