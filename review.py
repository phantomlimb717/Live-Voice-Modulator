import ast

with open("voice_modulator.py") as f:
    source = f.read()

tree = ast.parse(source)

for node in tree.body:
    if isinstance(node, ast.ClassDef) and node.name == "EditSoundDialog":
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                print("--- __init__ ---")
            if isinstance(item, ast.FunctionDef) and item.name == "accept":
                print("--- accept ---")
