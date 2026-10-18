
from app.graph_db import get_graph

graph = get_graph()

query = """
MATCH (t:Function {id: 'tests.test_requests:test_POSTBIN_GET_POST_FILES'})
OPTIONAL MATCH (t)-[:CALLS]->(f:Function)
RETURN t.id, collect(f.id)
"""

result = graph.query(query)

for row in result.result_set:
    print("Test:", row[0])
    print("Functions called directly:")
    for function in row[1]:
        if function:
            print(" ", function)
