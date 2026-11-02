import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

src = open(r"E:\qqbot\plugins\ai_chat\config.py", encoding="utf-8").read()
m = re.search(r"FISH_SYSTEM_PROMPT = \((.*?)\n\)", src, re.S)

ns = {
    "_STYLE_RULES": "",
    "_STICKER_RULES_FISH": "",
    "_SAVE_RULES_FISH": "",
    "_REMEMBER_RULES": "",
    "_SEARCH_RULES": "",
    "_GROUP_THREAD_RULES": "",
    "_ACTION_RULES": "",
}
block = eval("(" + m.group(1) + ")", ns)

start = block.find("性格：")
print(block[start:start + 700])
print("\n...\n")
idx = block.find("群友：今天挺好看")
print(block[idx:idx + 300])
