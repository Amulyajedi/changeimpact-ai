
import ast
import json
import sys
from pathlib import Path


def get_call_name(node):
    """Convert a function call into a readable dotted name."""
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = get_call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    # Handle awaited calls, such as: await client.post(...)
    if isinstance(node, ast.Await):
        return get_call_name(node.value)

    # Handle nested call expressions.
    if isinstance(node, ast.Call):
        return get_call_name(node.func)

    return None


def resolve_import_module(current_module, imported_module, level):
    """Resolve relative imports to project-style module names."""
    if level == 0:
        return imported_module or ""

    parts = current_module.split(".")
    package_parts = parts[:-1]

    # Each additional level moves one package higher.
    keep = max(0, len(package_parts) - level + 1)
    base_parts = package_parts[:keep]

    if imported_module:
        base_parts.extend(imported_module.split("."))

    return ".".join(base_parts)


class CallCollector(ast.NodeVisitor):
    """Collect calls without including nested functions' or classes' calls."""

    def __init__(self):
        self.calls = set()

    def visit_Call(self, node):
        name = get_call_name(node.func)

        if name:
            self.calls.add(name)

        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # Nested function calls belong to that nested function.
        return

    def visit_AsyncFunctionDef(self, node):
        return

    def visit_ClassDef(self, node):
        # Methods belong to the class, not the surrounding function.
        return


class FunctionCollector(ast.NodeVisitor):
    """Collect functions using class-aware and nested function IDs."""

    def __init__(self, module):
        self.module = module
        self.class_stack = []
        self.function_stack = []
        self.functions = []

    def visit_ClassDef(self, node):
        self.class_stack.append(node.name)

        for child in node.body:
            self.visit(child)

        self.class_stack.pop()

    def visit_FunctionDef(self, node):
        self._collect_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._collect_function(node)

    def _collect_function(self, node):
        scope = self.class_stack + self.function_stack + [node.name]
        qualified_name = ".".join(scope)

        call_collector = CallCollector()

        for statement in node.body:
            call_collector.visit(statement)

        self.functions.append({
            "id": f"{self.module}:{qualified_name}",
            "name": node.name,
            "module": self.module,
            "class": ".".join(self.class_stack) or None,
            "line": node.lineno,
            "calls": sorted(call_collector.calls),
        })

        # Also discover any functions nested inside this function.
        self.function_stack.append(node.name)

        for statement in node.body:
            self.visit(statement)

        self.function_stack.pop()


def parse_file(file_path, root):
    """Extract modules, functions, imports, and calls from a Python file."""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError, OSError) as error:
        print(f"Skipping {file_path}: {error}")
        return None

    module = file_path.relative_to(root).with_suffix("").as_posix()
    module = module.replace("/", ".")

    imports = []
    import_bindings = []

    # Preserve existing import extraction behavior.
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

                import_bindings.append({
                    "local": alias.asname or alias.name.split(".")[0],
                    "module": alias.name,
                    "name": None,
                    "kind": "module",
                })

        elif isinstance(node, ast.ImportFrom):
            resolved_module = resolve_import_module(
                module,
                node.module,
                node.level,
            )

            imports.append(resolved_module)

            for alias in node.names:
                if alias.name == "*":
                    continue

                import_bindings.append({
                    "local": alias.asname or alias.name,
                    "module": resolved_module,
                    "name": alias.name,
                    "kind": "symbol",
                })

    # Collect functions separately to preserve their class scope.
    collector = FunctionCollector(module)

    for node in tree.body:
        collector.visit(node)

    return {
        "module": module,
        "file": str(file_path),
        "imports": sorted(set(imports)),
        "import_bindings": import_bindings,
        "functions": collector.functions,
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
