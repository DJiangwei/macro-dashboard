import ast
import os
import glob
from collections import defaultdict

scripts = glob.glob("scripts/build_*_dashboard.py")

fetchers = []
for script in scripts:
    with open(script) as f:
        tree = ast.parse(f.read())
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith("fetch_") or node.name in ["_apply_transform", "_parse_period_date"]:
                    # check if we already have it
                    fetchers.append((node.name, script, ast.unparse(node)))

for name, script, code in fetchers:
    print(f"Function {name} from {script}")

