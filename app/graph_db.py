
from falkordb import FalkorDB


def get_graph():
    """Connect to FalkorDB and return our project graph."""
    db = FalkorDB(host="localhost", port=6379)
    return db.select_graph("ChangeImpact")


if __name__ == "__main__":
    graph = get_graph()
    result = graph.query("RETURN 'ChangeImpact AI connected!' AS message")
    print(result.result_set)
