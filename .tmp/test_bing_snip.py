import httpx, re, html
headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36","Accept-Language":"zh-CN,zh;q=0.9"}
r=httpx.get("https://cn.bing.com/search",params={"q":"DeepSeek 最新模型","mkt":"zh-CN"},headers=headers,timeout=15,follow_redirects=True)
for pat in [r'<p[^>]*class="[^"]*b_lineclamp[^"]*"[^>]*>(.*?)</p>', r'<div class="b_caption"[^>]*>.*?<p[^>]*>(.*?)</p>']:
    sn=re.findall(pat,r.text,re.S|re.I)
    print("PAT",len(sn))
    for x in sn[:3]: print(" ",re.sub(r"<[^>]+>","",html.unescape(x))[:160])
