import asyncio, importlib.util, sys
from pathlib import Path
import httpx
from dotenv import dotenv_values
ROOT=Path(".").resolve(); spec=importlib.util.spec_from_file_location("ai_config", ROOT/"plugins"/"ai_chat"/"config.py")
mod=importlib.util.module_from_spec(spec); sys.modules["ai_config"]=mod; spec.loader.exec_module(mod)
env=dotenv_values(ROOT/".env"); base=env["DEEPSEEK_BASE_URL"].rstrip("/")+"/chat/completions"; key=env["DEEPSEEK_API_KEY"]; model=env["DEEPSEEK_MODEL"]
async def main():
    msgs=[{"role":"system","content":mod.FISH_SYSTEM_PROMPT+"\n\n当前时间：2026-10-29 01:22（周四）"}]
    for text in ["在干嘛","你今天怎么这么安静","给我换个签名"]:
        msgs.append({"role":"user","content":text})
        p={"model":model,"messages":msgs,"temperature":1.1,"max_tokens":1500,"stream":False,"frequency_penalty":0.3,"presence_penalty":0.3}
        async with httpx.AsyncClient(timeout=90) as c:
            r=await c.post(base,json=p,headers={"Authorization":f"Bearer {key}"})
            reply=r.json()["choices"][0]["message"]["content"].strip()
        print(text,"=>",repr(reply)); msgs.append({"role":"assistant","content":reply}); await asyncio.sleep(1.2)
asyncio.run(main())
