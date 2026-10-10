import os
import re

files = [
    "scripts/build_china_dashboard.py",
    "scripts/build_uk_dashboard.py",
    "scripts/build_us_dashboard.py",
    "scripts/build_japan_dashboard.py",
    "scripts/build_south_africa_dashboard.py"
]

fetchers = {}

for f in files:
    with open(f, 'r') as file:
        content = file.read()
        
        # Regex to match def fetch_... until next def or end of file
        matches = re.finditer(r'^(def (?:_?fetch_[a-zA-Z0-9_]+|_safe_rows|_parse_date|_parse_period_date|_clean_text|_apply_transform)\(.*?(?:(?=\ndef )|\Z))', content, re.MULTILINE | re.DOTALL)
        for match in matches:
            func_code = match.group(1)
            func_name = re.match(r'^def ([a-zA-Z0-9_]+)', func_code).group(1)
            if func_name not in fetchers:
                fetchers[func_name] = func_code

with open('scratch/all_fetchers.py', 'w') as out:
    for name, code in fetchers.items():
        out.write(code + "\n\n")

print(f"Extracted {len(fetchers)} fetchers.")
