
import ast
import json
import sys
from pathlib import Path


def get_call_name(node):
    """Convert a function call into a readable name."""
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = get_call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return None


def parse_file(file_path, root):
    """Extract modules, functions, imports, and calls from one Python file."""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError, OSError) as error:
        print(f"Skipping {file_path}: {error}")
        return None

    module = file_path.relative_to(root).with_suffix("").as_posix()
    module = module.replace("/", ".")

    imports = []
    functions = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            calls = []

            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    name = get_call_name(child.func)
                    if name:
                        calls.append(name)

            functions.append({
                "id": f"{module}:{node.name}",
                "name": node.name,
                "module": module,
                "line": node.lineno,
                "calls": sorted(set(calls)),
            })

    return {
        "module": module,
        "file": str(file_path),
        "imports": sorted(set(imports)),
        "functions": functions,
    }


def scan_project(project_path):
    """Scan all Python files in a project directory."""
    root = Path(project_path).resolve()

    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    results = []

    for file_path in sorted(root.rglob("*.py")):
        result = parse_file(file_path, root)
        if result is not None:
            results.append(result)

    return results


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python app/ast_parser.py <project-folder>")
        sys.exit(1)

    try:
        results = scan_project(sys.argv[1])
        print(json.dumps(results, indent=2))
    except (NotADirectoryError, OSError) as error:
        print(f"Error: {error}")
        sys.exit(1)
