import requests, os

api_key = os.environ.get("FRED_API_KEY", "").strip()
if not api_key:
    # try loading from .env.local
    with open(".env.local") as f:
        for line in f:
            if "FRED_API_KEY" in line:
                api_key = line.split("=")[1].strip()

url = f"https://api.stlouisfed.org/fred/series/search?search_text=Emerging+Markets+Corporate+Plus+Index+Option-Adjusted+Spread&api_key={api_key}&file_type=json"
try:
    res = requests.get(url)
    data = res.json()
    for item in data.get("seriess", []):
        print(f"{item['id']}: {item['title']}")
except Exception as e:
    print(e)
