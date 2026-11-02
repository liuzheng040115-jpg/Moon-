import asyncio, os, sys
sys.path.insert(0, ".")
os.environ["AI_DB_PATH"] = ".tmp/searchtest.db"
import nonebot
nonebot.init()
from plugins.ai_chat import _web_search
result = asyncio.run(_web_search("今天 新闻"))
print("LEN", len(result))
print(result[:1200])
