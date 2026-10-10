import json, re

with open("output/japan_canonical_frame.json") as f:
    data = json.load(f)
    canonical = {item["indicator_id"] for item in data["series"]}

with open("output/japan.html") as f:
    html = f.read()
    divs = re.findall(r'id="chart-([^"]+)"', html)
    rendered = set(divs)

print("In canonical but not rendered:", canonical - rendered)
print("Rendered but not in canonical:", rendered - canonical)
