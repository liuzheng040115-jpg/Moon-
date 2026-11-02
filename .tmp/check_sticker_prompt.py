import sys

sys.path.insert(0, r"E:\qqbot\plugins")
sys.stdout.reconfigure(encoding="utf-8")

from ai_chat import memory  # noqa: E402

print("=== sticker_prompt ===")
print(memory.sticker_prompt(limit=20))
print("\n=== has_favorite_stickers ===")
print(memory.has_favorite_stickers())
