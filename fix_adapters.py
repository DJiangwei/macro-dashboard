import re

with open("src/country_primer/adapters.py", "r") as f:
    content = f.read()

# Add missing imports for dashboard_summary_utils to adapters.py
# since adapters is executed from the scripts directory usually, it can import dashboard_summary_utils
# but to be safe we can just move shift_calendar_periods into adapters.py.

with open("scripts/dashboard_summary_utils.py", "r") as f:
    utils_content = f.read()

match = re.search(r"def shift_calendar_periods.*?(?=\ndef [a-z]|\Z)", utils_content, re.DOTALL)
if match:
    shift_func = match.group(0)
else:
    shift_func = ""

content = content.replace("from email.utils import parsedate_to_datetime", "from email.utils import parsedate_to_datetime\n" + shift_func)
with open("src/country_primer/adapters.py", "w") as f:
    f.write(content)
