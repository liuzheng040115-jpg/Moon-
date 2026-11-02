import json
import sys
from pathlib import Path

import zstandard

sys.stdout.reconfigure(encoding="utf-8")

SRC = Path(
    r"C:\Users\86182\.dsh\sessions\--E-qqbot--\session-04cafe7e-2c6d-4553-ad29-089815180d00\session.v4.jsonl.zstd"
)

raw = SRC.read_bytes()
text = zstandard.ZstdDecompressor().decompress(raw, max_output_size=200_000_000).decode(
    "utf-8", "replace"
)
lines = [ln for ln in text.splitlines() if ln.strip()]
print(f"总行数: {len(lines)}")

# 先看结构
for ln in lines[:2]:
    try:
        obj = json.loads(ln)
        print("keys:", list(obj.keys()))
    except Exception as exc:
        print("解析失败:", exc)

out = Path(r"E:\qqbot\.tmp\session-04cafe7e.jsonl")
out.write_text("\n".join(lines), encoding="utf-8")
print("已导出:", out, out.stat().st_size, "字节")
