import yaml

with open("config/indicator_manifest_48.yaml") as f:
    manifest = yaml.safe_load(f)
with open("config/south_africa_indicators.yaml") as f:
    sa = yaml.safe_load(f)

sa_ids = {item["id"] for item in sa["indicators"]}
manifest_ids = {item["indicator_id"] for item in manifest["indicators"]}

missing = manifest_ids - sa_ids
print(f"South Africa is missing {len(missing)} indicators from the manifest:")
for idx in sorted(list(missing)):
    print(f"- {idx}")
