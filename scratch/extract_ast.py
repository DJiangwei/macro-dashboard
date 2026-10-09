import ast
from pathlib import Path

code = Path("scripts/build_china_dashboard.py").read_text()
tree = ast.parse(code)

names_to_extract = {
    "CSS", "_chart_html", "_format_value", "_gaps_html", "_json", 
    "_latest", "_section_nav", "_sections_html", "_write_clean", 
    "render_html", "_index_card", "inject_index", "_format_period", "_parse_year", "CHART_TEMPLATE",
    "SUMMARY_KEY_IDS"
}

output = []

for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in names_to_extract:
        # get source code of this node
        output.append(ast.get_source_segment(code, node))
    elif isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in names_to_extract:
                output.append(ast.get_source_segment(code, node))

Path("scratch/extracted_ui.py").write_text("\n\n".join(output))
