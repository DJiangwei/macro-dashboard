import yaml

with open("config/indicator_manifest_48.yaml") as f:
    manifest = yaml.safe_load(f)
with open("config/japan_indicators.yaml") as f:
    jp = yaml.safe_load(f)

jp_ids = {item["id"] for item in jp["indicators"]}
manifest_ids = {item["indicator_id"] for item in manifest["indicators"]}

missing = manifest_ids - jp_ids
print(f"Japan is missing {len(missing)} indicators from the manifest:")
for idx in sorted(list(missing)):
    print(f"- {idx}")
