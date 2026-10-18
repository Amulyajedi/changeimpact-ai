
from pathlib import Path
import sys

from ast_parser import scan_project
from graph_db import get_graph


def build_graph(project_path):
    graph = get_graph()
    results = scan_project(project_path)

    # Index all functions so calls can be resolved across modules.
    functions_by_id = {}
    functions_by_module_and_name = {}
    functions_by_name = {}
    modules = set()

    for module_data in results:
        module = module_data["module"]
        modules.add(module)

        for function in module_data["functions"]:
            functions_by_id[function["id"]] = function
            functions_by_module_and_name[(module, function["name"])] = function
            functions_by_name.setdefault(function["name"], []).append(function)

    function_count = 0

    # 1. Create or update function nodes without deleting existing data.
    for module_data in results:
        for function in module_data["functions"]:
            graph.query(
                """
                MERGE (f:Function {id: $id})
                SET f.name = $name,
                    f.module = $module,
                    f.line = $line
                """,
                {
                    "id": function["id"],
                    "name": function["name"],
                    "module": function["module"],
                    "line": function["line"],
                },
            )
            function_count += 1

    # 2. Resolve calls using local functions and import bindings.
    call_edges = set()

    for module_data in results:
        module = module_data["module"]
        bindings = module_data.get("import_bindings", [])

        module_aliases = {}
        symbol_aliases = {}

        for binding in bindings:
            if binding["kind"] == "module":
                module_aliases[binding["local"]] = binding["module"]
            elif binding["kind"] == "symbol":
                symbol_aliases[binding["local"]] = (
                    binding["module"],
                    binding["name"],
                )

        for function in module_data["functions"]:
            caller_id = function["id"]

            for call in function["calls"]:
                target = None

                # Direct call: helper(...)
                if "." not in call:
                    target = functions_by_module_and_name.get(
                        (module, call)
                    )

                    if not target and call in symbol_aliases:
                        target_module, target_name = symbol_aliases[call]
                        target = functions_by_module_and_name.get(
                            (target_module, target_name)
                        )

                    # Fallback only if the name is unique in the project.
                    if not target:
                        matches = functions_by_name.get(call, [])
                        if len(matches) == 1:
                            target = matches[0]

                else:
                    # Dotted call: alias.method(...) or module.func(...)
                    parts = call.split(".")
                    first = parts[0]

                    if first in symbol_aliases:
                        target_module, target_name = symbol_aliases[first]
                        remaining = ".".join(parts[1:])
                        if not remaining:
                            target = functions_by_module_and_name.get(
                                (target_module, target_name)
                            )

                    if not target and first in module_aliases:
                        target_module = module_aliases[first]
                        remaining = parts[1:]

                        if remaining:
                            candidate_module = ".".join(
                                [target_module] + remaining[:-1]
                            )
                            target = functions_by_module_and_name.get(
                                (candidate_module, remaining[-1])
                            )

                            if not target:
                                target = functions_by_module_and_name.get(
                                    (target_module, remaining[-1])
                                )

                    if not target:
                        # Handle calls through the current module name.
                        target = functions_by_module_and_name.get(
                            (module, parts[-1])
                        )

                if target and target["id"] != caller_id:
                    call_edges.add((caller_id, target["id"]))

    # 3. Add resolved CALLS relationships.
    for caller_id, callee_id in sorted(call_edges):
        graph.query(
            """
            MATCH (caller:Function {id: $caller_id})
            MATCH (callee:Function {id: $callee_id})
            MERGE (caller)-[:CALLS]->(callee)
            """,
            {
                "caller_id": caller_id,
                "callee_id": callee_id,
            },
        )

    print(f"Modules scanned: {len(results)}")
    print(f"Functions processed: {function_count}")
    print(f"Resolved call relationships: {len(call_edges)}")
    print("Existing graph data was preserved.")


if __name__ == "__main__":
    project_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "data/sample_repo"
    )
    build_graph(Path(project_path))
