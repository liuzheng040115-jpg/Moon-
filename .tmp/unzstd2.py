import sys
from pathlib import Path

import zstandard

sys.stdout.reconfigure(encoding="utf-8")

SRC = Path(
    r"C:\Users\86182\.dsh\sessions\--E-qqbot--\session-04cafe7e-2c6d-4553-ad29-089815180d00\session.v4.jsonl.zstd"
)

raw = SRC.read_bytes()
chunks = []
pos = 0
frames = 0

dctx = zstandard.ZstdDecompressor()

while pos < len(raw):
    try:
        obj = dctx.decompressobj()
        # 找到这一帧的边界：逐帧读取
        dobj = dctx.stream_reader(raw[pos:])
        chunk = dobj.read()
        if not chunk:
            break
        chunks.append(chunk)
        frames += 1
        # stream_reader 会吃掉整段（多帧连读），这里只需一次
        break
    except Exception as exc:
        print("失败:", exc)
        break

# 直接整体流式解（支持多帧）
with open(SRC, "rb") as f:
    data = f.read()

dctx = zstandard.ZstdDecompressor()
text = dctx.stream_reader(data).read().decode("utf-8", "replace")
lines = [ln for ln in text.splitlines() if ln.strip()]
print(f"解压后行数: {len(lines)}")

out = Path(r"E:\qqbot\.tmp\session-04cafe7e.jsonl")
out.write_text("\n".join(lines), encoding="utf-8")
print("已导出:", out, out.stat().st_size, "字节")
