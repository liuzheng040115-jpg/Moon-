import asyncio, importlib.util, sys
from pathlib import Path
import httpx
from dotenv import dotenv_values

ROOT = Path(".").resolve()
spec = importlib.util.spec_from_file_location("ai_config", ROOT / "plugins" / "ai_chat" / "config.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["ai_config"] = mod
spec.loader.exec_module(mod)
env = dotenv_values(ROOT / ".env")
base = env["DEEPSEEK_BASE_URL"].rstrip("/") + "/chat/completions"
key = env["DEEPSEEK_API_KEY"]
model = env["DEEPSEEK_MODEL"]

async def run(system, turns, label):
    print(f"\n===== {label} =====")
    messages = [{"role": "system", "content": system}]
    async with httpx.AsyncClient(timeout=90) as client:
        for text in turns:
            messages.append({"role": "user", "content": text})
            payload = {
                "model": model, "messages": messages, "temperature": 1.1,
                "max_tokens": 1500, "stream": False,
                "frequency_penalty": 0.3, "presence_penalty": 0.3,
            }
            try:
                r = await client.post(base, json=payload, headers={"Authorization": f"Bearer {key}"})
                data = r.json()
                reply = data["choices"][0]["message"]["content"].strip()
            except Exception as exc:
                print("ERR", type(exc).__name__, exc)
                return
            print(f"用户：{text}\n  回复：{reply!r}")
            messages.append({"role": "assistant", "content": reply})
            await asyncio.sleep(1.2)

asyncio.run(run(mod.FISH_SYSTEM_PROMPT, [
    "在吗", "你是真人吗", "发个表情包看看", "我今天好累", "英语能及格吗", "哈哈哈",
], "FISH"))
