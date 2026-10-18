
from pathlib import Path

from ast_parser import scan_project
from graph_db import get_graph


def build_graph(project_path):
    graph = get_graph()
    results = scan_project(project_path)

    # Clear the previous demo graph so reruns don't create duplicates.
    graph.query("MATCH (n) DETACH DELETE n")

    # Create a node for each function.
    for module_data in results:
        for function in module_data["functions"]:
            graph.query(
                """
                CREATE (:Function {
                    id: $id,
                    name: $name,
                    module: $module,
                    line: $line
                })
                """,
                {
                    "id": function["id"],
                    "name": function["name"],
                    "module": function["module"],
                    "line": function["line"],
                },
            )

    # Create CALLS edges between functions we can resolve.
    for module_data in results:
        for function in module_data["functions"]:
            for called_name in function["calls"]:
                graph.query(
                    """
                    MATCH (caller:Function {id: $caller_id})
                    MATCH (callee:Function {name: $callee_name})
                    WHERE caller.module = callee.module
                    CREATE (caller)-[:CALLS]->(callee)
                    """,
                    {
                        "caller_id": function["id"],
                        "callee_name": called_name,
                    },
                )

    print(f"Loaded {sum(len(m['functions']) for m in results)} functions.")


if __name__ == "__main__":
    sample_path = Path("data/sample_repo")
    build_graph(sample_path)
