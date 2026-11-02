import asyncio, os, sys
sys.path.insert(0, ".")
os.environ["AI_DB_PATH"] = ".tmp/searchtest.db"
import nonebot
nonebot.init()
from plugins.ai_chat import _web_search
print(asyncio.run(_web_search("DeepSeek 最新模型"))[:900])
