import importlib.util
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

spec = importlib.util.spec_from_file_location(
    "memory_mod", r"E:\qqbot\plugins\ai_chat\memory.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

store = mod.MemoryStore(db_path=r"E:\qqbot\data\bot.db")

now = time.time()
since = now - 24 * 3600

for label, ctype in (("群聊", "group"), ("全部", None)):
    rows = store.recent_chat(since, now, ctype, limit=300)
    print(f"=== 最近24小时 {label}: {len(rows)} 条 ===")
    kinds = {}
    for r in rows:
        kinds[r["chat_type"]] = kinds.get(r["chat_type"], 0) + 1
    print("  分布:", kinds)

# 只查群，看看最近 24 小时的群消息有多少
rows = store.recent_chat(since, now, "group", limit=300)
if rows:
    print("\n=== 最近几条群消息 ===")
    for r in rows[-5:]:
        t = time.strftime("%m-%d %H:%M", time.localtime(r["created"]))
        print(f"  [{t}] {r['chat_id']} {r['nickname']}: {str(r['content'])[:40]}")
