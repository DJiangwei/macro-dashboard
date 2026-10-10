import yaml

with open("config/framework_v2.yaml") as f:
    framework = yaml.safe_load(f)

with open("config/japan_indicators.yaml") as f:
    jp = yaml.safe_load(f)

jp_ids = {item["id"] for item in jp["indicators"]}

print("Japan has these IDs:")
print(sorted(list(jp_ids)))
print("---")

for item in framework["concepts"]:
    if not item["mappings"].get("JP"):
        # Let's see if we can guess an auto-match
        match = [jid for jid in jp_ids if jid in item["id"] or item["id"] in jid]
        print(f"Missing JP mapping for {item['id']} -> possible matches: {match}")
