with open("src/country_primer/adapters.py") as f:
    import ast
    tree = ast.parse(f.read())
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_parse_date":
            print(ast.unparse(node))
