import requests
import json
import urllib.parse
def search_fred(query):
    url = f"https://fred.stlouisfed.org/api/search?search_text={urllib.parse.quote(query)}"
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        data = res.json()
        for item in data.get("seriess", [])[:3]:
            print(f"{item['id']}: {item['title']} ({item['frequency_short']})")
    except:
        print("Failed", res.status_code)
search_fred("Japan housing starts")
search_fred("Japan vacancies")
search_fred("Japan consumer confidence")
search_fred("Japan consumption")
