import re
from pathlib import Path

path = Path("config/indicator_manifest_48.yaml")
text = path.read_text()

# We want to remove the specific block for sovereign_credit_spread_proxy
block1 = re.compile(r'- section_id: fiscal_sovereign\n\s+indicator_id: sovereign_credit_spread_proxy\n.*?executable credit protection pricing\.\n', re.DOTALL)
text = block1.sub('', text)

# And the block for local_currency_spread_vs_bund or sovereign_external_spread_proxy (which I renamed previously)
# Actually, I restored the file! So it is sovereign_external_spread_proxy!
block2 = re.compile(r'- section_id: markets_valuation\n\s+indicator_id: sovereign_external_spread_proxy\n.*?overlaps conceptually with the 10Y spread-vs-Bund chart\.\n', re.DOTALL)
text = block2.sub('', text)

path.write_text(text)
