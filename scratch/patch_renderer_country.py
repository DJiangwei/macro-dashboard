import re
from pathlib import Path

path = Path("src/country_primer/page_renderer.py")
text = path.read_text()

text = text.replace("<title>China Dashboard</title>", "<title>{config.get('name', 'Country')} Dashboard</title>")
text = text.replace('<h1><span data-lang="en">China Dashboard</span><span data-lang="zh">中国 Dashboard</span></h1>',
                    '<h1><span data-lang="en">{config.get("name", "Country")} Dashboard</span><span data-lang="zh">{config.get("name_zh", "Country")} Dashboard</span></h1>')
text = text.replace('href="china.html"', 'href="{config.get("name", "Country").lower().replace(" ", "_")}.html"')
text = text.replace('{_sections_html(config, series_list, "CN")}', '{_sections_html(config, series_list, config.get("iso2", "CN"))}')
text = text.replace('config/china_indicators.yaml', '{config.get("config_file", "indicators.yaml")}')
text = text.replace('data that matter for China', 'data that matter for {config.get("name", "Country")}')
text = text.replace('中的中国本土核心', '中的{config.get("name_zh", "该国")}本土核心')

path.write_text(text)
