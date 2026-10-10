import yaml

with open("config/framework_v2.yaml") as f:
    framework = yaml.safe_load(f)

jp_map = {
    "core_inflation": ["core_inflation"],
    "services_inflation": ["services_inflation"],
    "goods_inflation": ["goods_inflation"],
    "producer_price_inflation": ["producer_price_inflation"],
}

for item in framework["concepts"]:
    if item["id"] in jp_map:
        if "JP" not in item["mappings"]:
            item["mappings"]["JP"] = []
        item["mappings"]["JP"].extend(jp_map[item["id"]])

with open("config/framework_v2.yaml", "w") as f:
    yaml.dump(framework, f, sort_keys=False)
