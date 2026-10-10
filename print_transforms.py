def p(f):
    with open(f) as file:
        content = file.read()
        import ast
        tree = ast.parse(content)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == "_apply_transform":
                print(f"--- {f} ---")
                print(ast.unparse(node))
p("scripts/build_us_dashboard.py")
p("scripts/build_uk_dashboard.py")
p("scripts/build_china_dashboard.py")
