import yaml

with open("config/framework_v2.yaml") as f:
    framework = yaml.safe_load(f)

with open("config/south_africa_indicators.yaml") as f:
    sa = yaml.safe_load(f)

sa_ids = {item["id"] for item in sa["indicators"]}
print("SA has these IDs:")
print(sorted(list(sa_ids)))
print("---")

for item in framework["concepts"]:
    if not item["mappings"].get("ZA"):
        match = [sid for sid in sa_ids if sid in item["id"] or item["id"] in sid]
        print(f"Missing ZA mapping for {item['id']} -> possible matches: {match}")
