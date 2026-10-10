with open("src/country_primer/adapters.py") as f:
    lines = f.readlines()

import_lines = """
from datetime import date, timedelta
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET
from calendar import monthrange
from threading import Lock
from zipfile import ZipFile
from csv import DictReader
from io import StringIO
import time
"""

for i, line in enumerate(lines):
    if line.startswith("import requests"):
        lines.insert(i + 1, import_lines)
        break

with open("src/country_primer/adapters.py", "w") as f:
    f.writelines(lines)
