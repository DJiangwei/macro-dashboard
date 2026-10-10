import requests

try:
    res = requests.get("https://custom.resbank.co.za/SarbWebApi/WebIndicators/ReleaseOfSelectedData/MonthlyIndicatorsAll/MRDEI")
    data = res.json()
    for item in data:
        name = str(item.get("Description", "")) + " " + str(item.get("Name", ""))
        if "CDS" in name or "EMBI" in name or "Spread" in name.title() or "Risk" in name:
            print(f"{item.get('TimeseriesCode')}: {name}")
except Exception as e:
    print(e)
