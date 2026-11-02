import sys, os
sys.path.insert(0, ".")
os.environ["AI_DB_PATH"] = ".tmp/judge_test.db"
import nonebot
nonebot.init()
from plugins.ai_chat import _FILLER_ONLY, _looks_like_talking_to_others
cases = ["嗯", "？", "6", "草", "哈哈", "在吗", "@小王 你看这个", "他说的对", "帮我问一下他", "这个方案怎么改", "你们今晚吃啥"]
for c in cases:
    print(repr(c), "filler" if c in _FILLER_ONLY else "", "talk_to_others" if _looks_like_talking_to_others(c) else "")
