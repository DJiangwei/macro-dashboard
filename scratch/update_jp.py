import yaml

with open("config/japan_indicators.yaml") as f:
    jp = yaml.safe_load(f)

for item in jp["indicators"]:
    if item["id"] == "job_to_applicant_ratio":
        item["estat_tab"] = "200"
        
with open("config/japan_indicators.yaml", "w") as f:
    yaml.dump(jp, f, sort_keys=False, allow_unicode=True)
