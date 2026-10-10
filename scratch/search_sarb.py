import requests

try:
    res = requests.get("https://custom.resbank.co.za/SarbWebApi/WebIndicators/ReleaseOfSelectedData/MonthlyIndicatorsAll/MRDEI")
    data = res.json()
    for item in data:
        name = str(item.get("Description", "")) + " " + str(item.get("Name", ""))
        if "CPI" in name or "Consumer" in name or "Core" in name or "Manufacturing" in name:
            print(f"{item.get('TimeseriesCode')}: {name}")
except Exception as e:
    print(e)
