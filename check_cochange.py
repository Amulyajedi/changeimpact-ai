
from app.graph_db import get_graph

graph = get_graph()

query = """
MATCH (a:File)-[r:CO_CHANGED]-(b:File)
WHERE a.path = $path
RETURN b.path, r.count
ORDER BY r.count DESC
LIMIT 10
"""

result = graph.query(
    query,
    {"path": "src/requests/models.py"}
)

for row in result.result_set:
    print(row)

if not result.result_set:
    print("No co-change relationships found.")
