import asyncio, importlib.util, sys
from pathlib import Path
import httpx
from dotenv import dotenv_values

ROOT = Path(".").resolve()
spec = importlib.util.spec_from_file_location("ai_config", ROOT / "plugins" / "ai_chat" / "config.py")
mod = importlib.util.module_from_spec(spec); sys.modules["ai_config"] = mod; spec.loader.exec_module(mod)
env = dotenv_values(ROOT / ".env"); base = env["DEEPSEEK_BASE_URL"].rstrip("/") + "/chat/completions"
key, model = env["DEEPSEEK_API_KEY"], env["DEEPSEEK_MODEL"]

async def ask(system, user, label):
    msgs = [{"role":"system","content":system},{"role":"user","content":user}]
    payload = {"model":model,"messages":msgs,"temperature":1.1,"max_tokens":1500,"stream":False,
               "frequency_penalty":0.3,"presence_penalty":0.3}
    async with httpx.AsyncClient(timeout=90) as c:
        r = await c.post(base, json=payload, headers={"Authorization":f"Bearer {key}"})
        print(f"--- {label} ---")
        print(r.json()["choices"][0]["message"]["content"].strip())
        print()

async def main():
    await ask(mod.FISH_SYSTEM_PROMPT + "\n\n当前时间：2026-10-28 23:50（周三）",
              "记住我叫小明，我喜欢吃辣，周五要考试", "memory")
    group_ctx = """【最近的群聊，只用来理解上下文；“你”指你自己；不要逐条回应，也不要复述。先看“回复 #编号”/@ 的关系；有人说“问你呢/你自己看前面/刚才那句”时，按对应消息回答，不确定就问“你问哪句”】
[#001] 4 李知霖：不能自主发表情包吗?
[#002] 你：能啊 看心情
[#003] 4 李知霖：看谁的心情
[#004] 4 李知霖：[表情包]
[#005] 明天阵雨转晴：@Moon 问你呢"""
    await ask(mod.NORMAL_SYSTEM_PROMPT + "\n\n" + group_ctx + "\n\n当前时间：2026-10-28 23:50（周三）",
              "[这条 @ 了你]\n[你在回复 明天阵雨转晴 的消息：“@Moon 问你呢”]\n明天阵雨转晴：你自己看前面的消息呢",
              "group-thread")

asyncio.run(main())
