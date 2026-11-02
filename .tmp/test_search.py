import httpx
headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36","Accept-Language":"zh-CN,zh;q=0.9"}
for url,params in [("https://cn.bing.com/search",{"q":"今天新闻","format":"rss","mkt":"zh-CN"}),("https://www.bing.com/search",{"q":"今天新闻","format":"rss"}),("https://html.duckduckgo.com/html/",{"q":"今天新闻"})]:
    try:
        r=httpx.get(url,params=params,headers=headers,timeout=15,follow_redirects=True)
        print(url, r.status_code, len(r.text), r.text[:80].replace("\n"," "))
    except Exception as e:
        print(url, type(e).__name__, e)
