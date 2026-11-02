import httpx, re, html
headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36","Accept-Language":"zh-CN,zh;q=0.9"}
for q in ["今天有什么新闻","英伟达最新显卡","DeepSeek 最新模型"]:
    r=httpx.get("https://cn.bing.com/search",params={"q":q,"mkt":"zh-CN"},headers=headers,timeout=15,follow_redirects=True)
    print("Q",q,"status",r.status_code,"len",len(r.text))
    titles=re.findall(r'<h2[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>\s*</h2>',r.text,re.S|re.I)
    for link,title in titles[:4]:
        print(" -", re.sub(r"<[^>]+>","",html.unescape(title))[:80], link[:80])
