import httpx
from dotenv import dotenv_values
env = dotenv_values("E:/qqbot/.env")
base = env["DEEPSEEK_BASE_URL"].rstrip("/")
key = env["DEEPSEEK_API_KEY"]
print("key prefix:", key[:8], "len:", len(key))
try:
    r = httpx.get(base + "/models", headers={"Authorization": f"Bearer {key}"}, timeout=25)
    print("models status", r.status_code)
    if r.status_code == 200:
        ids = [m.get("id") for m in r.json().get("data", [])][:12]
        print("models:", ids)
except Exception as exc:
    print("models err", type(exc).__name__, exc)
try:
    r = httpx.post(base + "/chat/completions", headers={"Authorization": f"Bearer {key}"},
                   json={"model": env["DEEPSEEK_MODEL"], "messages": [{"role":"user","content":"说一句你好"}], "max_tokens": 200},
                   timeout=60)
    print("chat status", r.status_code)
    body = r.text[:300]
    print(body)
except Exception as exc:
    print("chat err", type(exc).__name__, exc)
