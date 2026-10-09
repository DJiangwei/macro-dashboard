import ast
from collections import defaultdict
import builtins

code = open("src/country_primer/page_renderer.py").read()
tree = ast.parse(code)

defined = set(dir(builtins))
used = set()

for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for name in node.names:
            defined.add(name.asname or name.name.split('.')[0])
    elif isinstance(node, ast.ImportFrom):
        for name in node.names:
            defined.add(name.asname or name.name)
    elif isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                defined.add(target.id)
    elif isinstance(node, ast.FunctionDef):
        defined.add(node.name)
        for arg in node.args.args:
            defined.add(arg.arg)
    elif isinstance(node, ast.Name):
        if isinstance(node.ctx, ast.Load):
            used.add(node.id)
        elif isinstance(node.ctx, ast.Store):
            defined.add(node.id)

print(sorted(used - defined))
