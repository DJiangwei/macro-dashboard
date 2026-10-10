import yaml
with open("config/south_africa_indicators.yaml") as f:
    config = yaml.safe_load(f)
fetchers = set()
for ind in config.get("indicators", []):
    fetchers.add(ind.get("fetcher"))
print("Config fetchers:", fetchers)
