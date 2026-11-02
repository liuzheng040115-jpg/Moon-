import sys, os
sys.path.insert(0, ".")
os.environ["AI_DB_PATH"] = ".tmp/tone_test.db"
import nonebot
nonebot.init()
from plugins.ai_chat import _tone_down_particles, _humanize_text
for s in ["还在呢 你先睡", "好呀 这就去啦", "在呢在呢", "嗯呢 好呀 行吧啦"]:
    t = _tone_down_particles(s)
    print(repr(s), "-> tone", repr(t), "-> final", repr(_humanize_text(t)))
