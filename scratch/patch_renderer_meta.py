import re
from pathlib import Path

path = Path("src/country_primer/page_renderer.py")
text = path.read_text()

old_meta = """    <div class="meta-row">
      <span class="meta-chip">{chart_count} <span data-lang="en">charts</span><span data-lang="zh">张图</span></span>
      <span class="meta-chip">{source_count} <span data-lang="en">public source groups</span><span data-lang="zh">组公开来源</span></span>
      <span class="meta-chip">{gap_count} <span data-lang="en">official-data gaps tracked</span><span data-lang="zh">个官方数据缺口</span></span>
      <span class="meta-chip">{low_count} <span data-lang="en">low-confidence charts</span><span data-lang="zh">张低置信图</span></span>
    </div>"""

new_meta = """    native = sum(1 for item in series_list if item.get("source_authority") == "official primary" and item.get("observations"))
    mirror = sum(1 for item in series_list if item.get("source_authority") == "official mirror" and item.get("observations"))
    
    meta_row = f'''<div class="meta-row">
      <span class="meta-chip">{chart_count} <span data-lang="en">charts</span><span data-lang="zh">张图</span></span>
      <span class="meta-chip">{source_count} <span data-lang="en">public source groups</span><span data-lang="zh">组公开来源</span></span>
      <span class="meta-chip">{gap_count} <span data-lang="en">official-data gaps tracked</span><span data-lang="zh">个官方数据缺口</span></span>
      <span class="meta-chip">{low_count} <span data-lang="en">low-confidence charts</span><span data-lang="zh">张低置信图</span></span>
      <span class="meta-chip">{native} <span data-lang="en">native official</span><span data-lang="zh">原生官方</span> · {mirror} <span data-lang="en">mirror</span><span data-lang="zh">镜像</span></span>
    </div>'''"""

# Wait, `meta_row` is in an f-string!
# The original code uses an f-string for the whole HTML block.
