import yaml

with open("config/japan_indicators.yaml") as f:
    jp = yaml.safe_load(f)

for item in jp["indicators"]:
    print(item["id"])
