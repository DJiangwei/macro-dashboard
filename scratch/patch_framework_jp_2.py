import yaml

with open("config/framework_v2.yaml") as f:
    framework = yaml.safe_load(f)

jp_map = {
    "vacancies": ["job_to_applicant_ratio"],
    "housing_activity": ["housing_starts"]
}

for item in framework["concepts"]:
    c_id = item["id"]
    if c_id in jp_map:
        if "JP" not in item["mappings"]:
            item["mappings"]["JP"] = []
        for val in jp_map[c_id]:
            if val not in item["mappings"]["JP"]:
                item["mappings"]["JP"].append(val)

with open("config/framework_v2.yaml", "w") as f:
    yaml.dump(framework, f, sort_keys=False)
