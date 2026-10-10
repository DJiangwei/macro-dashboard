import ast
import os
import glob

exclude = {
    "_load_config", "_json", "_write_clean", "_latest", "_format_period",
    "_format_value", "_chart_html", "_render_cards", "_key_series_latest",
    "_section_nav", "_sections_html", "_gaps_html", "_index_card", "inject_index",
    "build", "validate_series", "fetch_all", "inject_output_index", "inject_root_index",
    "_chart_latest_reading", "_format_chart_reading", "render_html", "build_country_page",
    "main", "apply_quality_assessments", "build_summary_metadata", "canonical_frame_metadata",
    "load_canonical_data_first_frame", "retain_last_known_good_series", "track_revisions_and_vintages",
    "write_canonical_data_first_frame"
}

def extract_from(filename, rename_map):
    with open(filename) as f:
        source = f.read()
    
    tree = ast.parse(source)
    extracted = []
    
    class Rewriter(ast.NodeTransformer):
        def visit_Name(self, node):
            if node.id in rename_map:
                node.id = rename_map[node.id]
            return node
        def visit_FunctionDef(self, node):
            if node.name in rename_map:
                node.name = rename_map[node.name]
            self.generic_visit(node)
            return node
        def visit_Call(self, node):
            # Also catch calls to renamed functions
            if isinstance(node.func, ast.Name) and node.func.id in rename_map:
                node.func.id = rename_map[node.func.id]
            self.generic_visit(node)
            return node

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if node.name not in exclude:
                Rewriter().visit(node)
                extracted.append(ast.unparse(node))
            
    return "\n\n".join(extracted)

us_funcs = extract_from("scripts/build_us_dashboard.py", {"_apply_transform": "_apply_us_transform"})
uk_funcs = extract_from("scripts/build_uk_dashboard.py", {"_apply_transform": "_apply_uk_transform"})
china_funcs = extract_from("scripts/build_china_dashboard.py", {"_apply_transform": "_apply_china_transform"})
za_funcs = extract_from("scripts/build_south_africa_dashboard.py", {})

with open("src/country_primer/adapters.py", "a") as f:
    f.write("\n\n" + us_funcs)
    f.write("\n\n" + uk_funcs)
    f.write("\n\n" + china_funcs)
    f.write("\n\n" + za_funcs)

print("Extraction done.")
