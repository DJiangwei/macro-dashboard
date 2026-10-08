import re
from pathlib import Path

files_to_update = [
    "scripts/build_us_dashboard.py",
    "scripts/build_uk_dashboard.py",
    "scripts/build_china_dashboard.py",
    "scripts/build_south_africa_dashboard.py",
    "scripts/build_japan_dashboard.py",
]

for file_path in files_to_update:
    path = Path(file_path)
    content = path.read_text()
    
    # Add import
    content = re.sub(
        r'retain_last_known_good_series,',
        r'retain_last_known_good_series,\n    track_revisions_and_vintages,',
        content,
        count=1
    )
    
    # Add function call
    content = re.sub(
        r'(series_list = retain_last_known_good_series\(series_list, CANONICAL_JSON, config\))',
        r'\1\n        series_list = track_revisions_and_vintages(series_list, CANONICAL_JSON, config)',
        content,
        count=1
    )
    
    path.write_text(content)
