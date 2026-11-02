import base64
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

KEY = None
with open(r"C:\Users\86182\.dsh\.credentials.yaml", encoding="utf-8") as f:
    for line in f:
        if "GPT_API_KEY:" in line:
            KEY = line.split(":", 1)[1].strip()
            break

if not KEY:
    raise SystemExit("没找到 GPT_API_KEY")

BASE = "https://heilovehei.com/v1"

payload = {
    "model": "gpt-image-2",
    "prompt": "a simple blue cartoon whale, flat design, white background",
    "n": 1,
    "size": "1024x1024",
}

req = urllib.request.Request(
    BASE + "/images/generations",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": "Bearer " + KEY,
        "Content-Type": "application/json",
    },
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    print("HTTP OK")
    print("keys:", list(body.keys()))
    item = body["data"][0]
    print("item keys:", list(item.keys()))
    if item.get("b64_json"):
        raw = base64.b64decode(item["b64_json"])
        out = r"E:\qqbot\.tmp\test_gen.png"
        with open(out, "wb") as f:
            f.write(raw)
        print("saved:", out, len(raw), "bytes")
    elif item.get("url"):
        print("url:", item["url"][:120])
except urllib.error.HTTPError as exc:
    print("HTTP", exc.code)
    print(exc.read().decode("utf-8", "replace")[:800])
except Exception as exc:
    print("失败:", type(exc).__name__, exc)
