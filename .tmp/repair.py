from pathlib import Path

src = Path("plugins/ai_chat/__init__.py")
raw = src.read_text(encoding="utf-8")
out = bytearray()
for ch in raw:
    code = ord(ch)
    if code < 128:
        out.append(code)
        continue
    try:
        out.extend(ch.encode("cp1252"))
    except UnicodeEncodeError:
        try:
            out.extend(ch.encode("latin-1"))
        except UnicodeEncodeError:
            out.extend(b"?")

fixed = out.decode("utf-8", errors="replace")
Path(".tmp/repaired_init.py").write_text(fixed, encoding="utf-8")
print("replacement chars:", fixed.count("\ufffd"))
for line in fixed.splitlines():
    if "_PROFILE_KEYWORDS" in line or "头像" in line or "毒舌" in line:
        print(line)
