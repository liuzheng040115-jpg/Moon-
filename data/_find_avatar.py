"""抓一批候选头像图（百度 + DuckDuckGo），拼成联络表方便挑。"""

from __future__ import annotations

import io
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(r"E:\qqbot")
OUT = ROOT / "data" / "candidates"
OUT.mkdir(parents=True, exist_ok=True)

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def fetch(url: str, referer: str = "", timeout: int = 25) -> bytes:
    headers = dict(UA)
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def baidu(q: str, page: int = 0) -> list[str]:
    url = (
        "https://image.baidu.com/search/acjson?tn=resultjson_com&ipn=rj&ct=201326592"
        "&is=&fp=result&fr=&word=%s&queryWord=%s&cl=2&lm=-1&ie=utf-8&oe=utf-8"
        "&st=-1&z=&ic=0&hd=&latest=&copyright=&s=&se=&tab=&width=&height=&face=0"
        "&istype=2&qc=&nc=1&expermode=&nojc=&isAsync=&pn=%d&rn=30&gsm=%x"
        % (urllib.parse.quote(q), urllib.parse.quote(q), page * 30, page * 30)
    )
    raw = fetch(url, referer="https://image.baidu.com/").decode("utf-8", "replace")
    out = []
    for key in ("hoverURL", "middleURL", "thumbURL"):
        out += [u.replace("\\/", "/") for u in re.findall(r'"%s":"(.*?)"' % key, raw)]
    return out


def ddg(q: str) -> list[str]:
    html = fetch("https://duckduckgo.com/?q=%s&iax=images&ia=images" % urllib.parse.quote(q)).decode(
        "utf-8", "replace"
    )
    m = re.search(r"vqd=['\"]?([\d-]+)", html)
    if not m:
        return []
    vqd = m.group(1)
    data = json.loads(
        fetch(
            "https://duckduckgo.com/i.js?l=wt-wt&o=json&q=%s&vqd=%s&f=,,,&p=1"
            % (urllib.parse.quote(q), vqd),
            referer="https://duckduckgo.com/",
        ).decode("utf-8", "replace")
    )
    return [r["image"] for r in data.get("results", [])]


QUERIES = [
    ("baidu", "可爱 胖鱼 插画"),
    ("baidu", "大肥鱼 表情包 可爱"),
    ("baidu", "河豚 可爱 插画"),
    ("ddg", "cute chubby fish illustration"),
    ("ddg", "kawaii fat fish cartoon"),
]

urls: list[str] = []
for kind, q in QUERIES:
    try:
        got = baidu(q) if kind == "baidu" else ddg(q)
    except Exception as exc:
        print("FAIL", kind, q, exc)
        continue
    add = 0
    for u in got:
        if u.startswith("http") and u not in urls:
            urls.append(u)
            add += 1
    print(f"{kind}:{q} -> +{add} (total {len(urls)})")

saved: list[Path] = []
for u in urls[:80]:
    try:
        blob = fetch(u, referer="https://image.baidu.com/")
        im = Image.open(io.BytesIO(blob))
        im.load()
        w, h = im.size
        if min(w, h) < 380 or not (0.62 < w / h < 1.6):
            continue
        im.convert("RGB").save(OUT / f"c{len(saved) + 1:02d}.png")
        saved.append(OUT / f"c{len(saved) + 1:02d}.png")
    except Exception:
        continue

print("SAVED", len(saved))

TH, COLS = 220, 6
rows = max(1, (len(saved) + COLS - 1) // COLS)
sheet = Image.new("RGB", (COLS * TH, rows * TH), (245, 245, 245))
d = ImageDraw.Draw(sheet)
for idx, p in enumerate(saved):
    im = Image.open(p).convert("RGB")
    im.thumbnail((TH - 8, TH - 8))
    x = (idx % COLS) * TH + (TH - im.width) // 2
    y = (idx // COLS) * TH + (TH - im.height) // 2
    sheet.paste(im, (x, y))
    d.rectangle(
        [idx % COLS * TH, idx // COLS * TH, idx % COLS * TH + TH - 1, idx // COLS * TH + TH - 1],
        outline=(210, 210, 210),
    )
    d.text((idx % COLS * TH + 6, idx // COLS * TH + 4), str(idx + 1), fill=(220, 30, 30))

sheet.save(ROOT / "data" / "montage.png")
print("MONTAGE", sheet.size)
