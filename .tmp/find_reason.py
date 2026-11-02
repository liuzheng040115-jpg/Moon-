import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SRC = Path(r"E:\qqbot\.tmp\session-04cafe7e.jsonl")

KEYWORDS = [
    "掉线", "断线", "离线", "重启", "为什么", "原因",
    "休眠", "睡眠", "关机", "自启", "断开", "断开连接",
    "没响应", "离线通知",
]

hits = []
for idx, line in enumerate(SRC.read_text(encoding="utf-8").splitlines()):
    if not line.strip():
        continue
    try:
        obj = json.loads(line)
    except Exception:
        continue
    blob = json.dumps(obj, ensure_ascii=False)
    if not any(k in blob for k in ("掉线", "断线", "休眠", "睡眠", "自启", "关机")):
        continue
    hits.append((idx, obj, blob))

print(f"命中 {len(hits)} 行\n")

for idx, obj, blob in hits[:40]:
    typ = obj.get("type", "?")
    print(f"--- 行 {idx}  类型 {typ} ---")
    # 抽取可读文本
    text = blob
    for key in ("text", "content", "message", "data"):
        node = obj.get(key)
        if isinstance(node, str) and len(node) > 20:
            text = node
            break
        if isinstance(node, list):
            parts = []
            for item in node:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item, str):
                    parts.append(item)
            if parts:
                text = "\n".join(parts)
                break
    print(text[:900])
    print()
