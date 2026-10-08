import re

with open("scripts/dashboard_summary_utils.py", "r") as f:
    content = f.read()

# Fix the duplicate output block
bad_block = """                                    "refresh_fallback": bool(item.get("refresh_fallback")),
            "fetch_timestamp": _clean(item.get("fetch_timestamp")),
            "has_revisions": bool(item.get("has_revisions")),
            "prior_vintage": item.get("prior_vintage"),
            "fetch_timestamp": _clean(item.get("fetch_timestamp")),
            "has_revisions": bool(item.get("has_revisions")),
            "prior_vintage": item.get("prior_vintage"),"""

good_block = """            "refresh_fallback": bool(item.get("refresh_fallback")),
            "fetch_timestamp": _clean(item.get("fetch_timestamp")),
            "has_revisions": bool(item.get("has_revisions")),
            "prior_vintage": item.get("prior_vintage"),"""

content = content.replace(bad_block, good_block)

# And check load_canonical_data_first_frame
bad_restore = """            "refresh_fallback": bool(item.get("refresh_fallback")),
            "fetch_timestamp": _clean(item.get("fetch_timestamp")),
            "has_revisions": bool(item.get("has_revisions")),
            "prior_vintage": item.get("prior_vintage"),"""
if content.count(bad_restore) > 1:
    pass # Wait, if it didn't duplicate there, it's fine.

with open("scripts/dashboard_summary_utils.py", "w") as f:
    f.write(content)
