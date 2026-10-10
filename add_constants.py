constants = """
SARB_BASE = "https://custom.resbank.co.za/SarbWebApi/WebIndicators/Shared/GetTimeseriesObservations"
FRED_GRAPH_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES_URL = "https://api.stlouisfed.org/fred/series"
BOE_BANK_RATE_URL = "https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp?hl=en-GB"
BOE_IADB_URL = "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
ONS_TIMESERIES_BASE = "https://www.ons.gov.uk"
BINARY_DOWNLOAD_CACHE_LOCK = Lock()
DISTRIBUTION_CACHE_LOCK = Lock()
MONTHS = {
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04", "MAY": "05", "JUN": "06",
    "JUL": "07", "AUG": "08", "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
}
TREASURY_AUCTIONS_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"
BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
import threading
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
BLS_BED_CACHE_PATH = ROOT / "data" / "us_bls_bed_cache.json"
BLS_LOCK = threading.Lock()
"""

with open("src/country_primer/adapters.py", "r") as f:
    content = f.read()

content = content.replace("import time\n", "import time\n" + constants + "\n")
with open("src/country_primer/adapters.py", "w") as f:
    f.write(content)
