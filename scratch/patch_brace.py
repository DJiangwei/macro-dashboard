with open("scripts/macro_workbench.py", "r") as f:
    text = f.read()
text = text.replace("    }\n    }", "    }")
with open("scripts/macro_workbench.py", "w") as f:
    f.write(text)
