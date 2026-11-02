import sys, os
sys.path.insert(0, ".")
os.environ["AI_DB_PATH"] = ".tmp/tone_test.db"
import nonebot
nonebot.init()
from plugins.ai_chat import _tone_down_particles
samples = [
    "好呀。我这就去啦～",
    "还在呢",
    "这就来啦",
    "好嘛 不说了",
    "对哦 我忘了",
    "行吧",
    "你干嘛呢",
    "哎哟 这么晚",
    "好耶好耶好耶",
    "在呢在呢",
]
for s in samples:
    print(repr(s), "->", repr(_tone_down_particles(s)))
