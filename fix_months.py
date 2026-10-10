with open("src/country_primer/adapters.py", "r") as f:
    content = f.read()

import re
# Find the bad MONTHS dict
content = re.sub(r'MONTHS = \{[^}]+\}', '', content)

good_months = """
MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
"""

content = content.replace("DISTRIBUTION_CACHE_LOCK = Lock()", "DISTRIBUTION_CACHE_LOCK = Lock()\n" + good_months)

with open("src/country_primer/adapters.py", "w") as f:
    f.write(content)
