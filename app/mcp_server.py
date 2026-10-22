
from pathlib import Path
import sys

# Ensure existing application modules can be imported.
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from mcp.server.fastmcp import FastMCP
from graph_db import get_graph
from impact_analysis import trace_impact

mcp = FastMCP(
    "ChangeImpact Voice",
    host="127.0.0.1",
    port=8000,
)


@mcp.tool()
def search_functions(search_term: str, limit: int = 10) -> dict:
    """Find functions in the ChangeImpact dependency graph by name or module."""
    term = search_term.strip()
    if not term:
        return {"error": "Enter a function name or module."}

    limit = max(1, min(int(limit), 30))

    try:
        graph = get_graph()
        result = graph.query(
            """
            MATCH (f:Function)
            WHERE toLower(f.id) CONTAINS toLower($term)
               OR toLower(f.name) CONTAINS toLower($term)
               OR toLower(f.module) CONTAINS toLower($term)
            RETURN f.id, f.name, f.module, f.line
            ORDER BY f.id
            LIMIT $limit
            """,
            {"term": term, "limit": limit},
        )

        functions = [
            {
                "id": row[0],
                "name": row[1],
                "module": row[2],
                "line": row[3],
            }
            for row in result.result_set
        ]

        return {
            "search_term": term,
            "count": len(functions),
            "functions": functions,
        }

    except Exception as exc:
        return {"error": f"Function search failed: {exc}"}


@mcp.tool()
def analyze_change_impact(
    changed_function_id: str,
    max_depth: int = 5,
) -> dict:
    """Find callers potentially affected by a changed function, connected tests,
    and historical co-changed files using the existing analysis backend."""
    function_id = changed_function_id.strip()
    if not function_id:
        return {"error": "Provide the exact function ID."}

    max_depth = max(1, min(int(max_depth), 10))

    try:
        graph = get_graph()

        exists = graph.query(
            """
            MATCH (f:Function {id: $function_id})
            RETURN f.id
            LIMIT 1
            """,
            {"function_id": function_id},
        )

        if not exists.result_set:
            return {
                "error": "Function ID not found in the graph.",
                "changed_function_id": function_id,
                "hint": "Use search_functions to find a valid function ID.",
            }

        impacted, tests, historical_files = trace_impact(
            function_id,
            max_depth=max_depth,
        )

        return {
            "changed_function_id": function_id,
            "max_depth": max_depth,
            "potentially_affected_functions": [
                {
                    "id": function_id,
                    "name": details["name"],
                    "dependency_distance": details["hops"],
                }
                for function_id, details in sorted(
                    impacted.items(),
                    key=lambda item: (
                        item[1]["hops"],
                        item[0],
                    ),
                )
            ],
            "recommended_connected_tests": [
                {
                    "id": test_id,
                    "dependency_distance": distance,
                }
                for test_id, distance in sorted(
                    tests.items(),
                    key=lambda item: (item[1], item[0]),
                )
            ],
            "historically_cochanged_files": [
                {
                    "path": path,
                    "change_together_count": count,
                }
                for path, count in sorted(
                    historical_files.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ],
            "note": (
                "These are graph-based candidates, not proof that a change "
                "will cause a failure. Historical co-changes are correlations."
            ),
        }

    except Exception as exc:
        return {"error": f"Impact analysis failed: {exc}"}


@mcp.tool()
def get_historical_cochanges(file_path: str, limit: int = 10) -> dict:
    """Find files historically changed together with a repository file."""
    path = file_path.strip()
    if not path:
        return {"error": "Provide a repository-relative file path."}

    limit = max(1, min(int(limit), 30))

    try:
        graph = get_graph()
        result = graph.query(
            """
            MATCH (a:File)-[r:CO_CHANGED]-(b:File)
            WHERE a.path = $path
            RETURN b.path, r.count
            ORDER BY r.count DESC
            LIMIT $limit
            """,
            {"path": path, "limit": limit},
        )

        files = [
            {
                "path": row[0],
                "change_together_count": row[1],
            }
            for row in result.result_set
            if row[0] is not None
        ]

        return {
            "file_path": path,
            "count": len(files),
            "historical_cochanges": files,
            "note": "Historical co-changes indicate correlation, not causation.",
        }

    except Exception as exc:
        return {"error": f"Historical co-change lookup failed: {exc}"}


if __name__ == "__main__":
    print("Starting ChangeImpact Voice MCP server...")
    print("Streamable HTTP endpoint: http://127.0.0.1:8000/mcp")
    mcp.run(transport="streamable-http")
