import importlib.util
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

tmp = Path(r"E:\qqbot\.tmp\purge-test2.db")
if tmp.exists():
    tmp.unlink()

spec = importlib.util.spec_from_file_location(
    "memory_mod", r"E:\qqbot\plugins\ai_chat\memory.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

store = mod.MemoryStore(db_path=str(tmp))
con = sqlite3.connect(str(tmp))

# 造一段没有检修的对话
con.executemany(
    "INSERT INTO chat_log(chat_type, chat_id, user_id, nickname, content, is_bot, created) "
    "VALUES ('private','1450520453',1450520453,'他',?,?,?)",
    [
        ("今天天气不错", 0, 100.0),
        ("是挺好", 1, 101.0),
        ("出去走走", 0, 102.0),
    ],
)
con.commit()
before = con.execute("SELECT COUNT(*) FROM chat_log").fetchone()[0]

removed = store.purge_maintenance_traces("1450520453")
after = con.execute("SELECT COUNT(*) FROM chat_log").fetchone()[0]

print(f"清理前 {before} 条，删了 {removed} 条，剩 {after} 条")
print("结论:", "没有误删" if after == before else "有误删！")
con.close()
