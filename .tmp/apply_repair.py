from pathlib import Path

src = Path("plugins/ai_chat/__init__.py")
fixed = Path(".tmp/repaired_init.py").read_text(encoding="utf-8")
old = '_PROFILE_KEYWORDS = ("头像", "昵称", "签名", "改名", "换名", "名字", "资料", "名片")'
new = '_PROFILE_KEYWORDS = ("头像", "昵称", "签名", "改名", "换名", "换名字", "名字换", "名字改", "资料", "名片")'
if old not in fixed:
    raise SystemExit("keyword line not found; aborting")
fixed = fixed.replace(old, new)
src.write_text(fixed, encoding="utf-8")
print("restored and patched", len(fixed), "chars")
