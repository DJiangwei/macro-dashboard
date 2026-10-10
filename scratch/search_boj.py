import urllib.request
import re
url = "https://www.stat-search.boj.or.jp/ssi/cgi-bin/famecgi2?cgi=$nme_a000_en"
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req).read().decode('utf-8')
    print("Fetched BOJ main page, size:", len(html))
    print(re.findall(r'href=.*?mtshtml.*?\.zip', html))
except Exception as e:
    print(e)
