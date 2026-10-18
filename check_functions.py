
from app.graph_db import get_graph

graph = get_graph()

result = graph.query(
    """
    MATCH (f:Function)
    WHERE f.module = $module
    RETURN f.id, f.name
    LIMIT 10
    """,
    {"module": "src.requests.models"},
)

print("Functions found:")
for row in result.result_set:
    print(row)

if not result.result_set:
    print("No functions found for this module.")
