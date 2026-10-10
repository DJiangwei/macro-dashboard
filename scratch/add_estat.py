import yaml
with open("config/japan_indicators.yaml") as f:
    jp = yaml.safe_load(f)

# Add Job-to-applicant ratio
jp["indicators"].append({
    "id": "job_to_applicant_ratio",
    "section": "labour_market",
    "label_en": "Job-to-Applicant Ratio",
    "label_zh": "有效求人倍率",
    "unit": "ratio",
    "fetcher": "estat",
    "stats_data_id": "0003446462",
    "estat_cat01": "2090",
    "series": "0003446462/-/2090" # dummy series key for cache/unique ID
})

# Add Housing Starts
jp["indicators"].append({
    "id": "housing_starts",
    "section": "housing_construction",
    "label_en": "Housing Starts (Total Units)",
    "label_zh": "新设住宅着工户数",
    "unit": "units",
    "fetcher": "estat",
    "stats_data_id": "0003114496",
    "estat_tab": "19",
    "estat_cat01": "11",
    "estat_cat02": "11",
    "estat_cat03": "11",
    "estat_area": "00000",
    "series": "0003114496/19/11/11/11/00000"
})

with open("config/japan_indicators.yaml", "w") as f:
    yaml.dump(jp, f, sort_keys=False, allow_unicode=True)
