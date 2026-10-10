import json

with open("output/japan_canonical_frame.json") as f:
    data = json.load(f)
    print("Series length:", len(data.get("series", [])))

with open("output/japan.html") as f:
    html = f.read()
    import re
    print("Cards:", len(re.findall(r'class="chart-card', html)))
