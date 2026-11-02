import importlib.util
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# 复制一份库来试，不动真数据
src = Path(r"E:\qqbot\data\bot.db")
tmp = Path(r"E:\qqbot\.tmp\purge-test.db")
for suffix in ("", "-wal", "-shm"):
    p = Path(str(src) + suffix)
    if p.exists():
        Path(str(tmp) + suffix).write_bytes(p.read_bytes())

spec = importlib.util.spec_from_file_location(
    "memory_mod", r"E:\qqbot\plugins\ai_chat\memory.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

store = mod.MemoryStore(db_path=str(tmp))

con = sqlite3.connect(str(tmp))
print("=== 清理前：最近 6 条 chat_log ===")
for row in con.execute(
    "SELECT id, is_bot, content FROM chat_log WHERE chat_id='1450520453' ORDER BY id DESC LIMIT 6"
):
    print(row[0], "她" if row[1] else "他", str(row[2])[:50])
con.close()

removed = store.purge_maintenance_traces("1450520453")
print(f"\n删掉 {removed} 条")

con = sqlite3.connect(str(tmp))
print("\n=== 清理后：最近 6 条 chat_log ===")
for row in con.execute(
    "SELECT id, is_bot, content FROM chat_log WHERE chat_id='1450520453' ORDER BY id DESC LIMIT 6"
):
    print(row[0], "她" if row[1] else "他", str(row[2])[:50])
con.close()
