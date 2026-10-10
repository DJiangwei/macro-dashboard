import yaml
import re

with open("config/indicator_manifest_48.yaml") as f:
    manifest = yaml.safe_load(f)
    
manifest_map = {}
for item in manifest["indicators"]:
    # map by label
    label_en = item.get("label", "").lower()
    manifest_map[label_en] = item["indicator_id"]
    
def map_country(filename):
    with open(filename) as f:
        config = yaml.safe_load(f)
        
    for item in config.get("indicators", []):
        label_en = item.get("label_en", "").lower()
        if label_en in manifest_map:
            print(f"{item['id']} -> {manifest_map[label_en]}")
            item["id"] = manifest_map[label_en]
        else:
            print(f"NO MATCH FOR: {label_en} ({item['id']})")
            
map_country("config/japan_indicators.yaml")
