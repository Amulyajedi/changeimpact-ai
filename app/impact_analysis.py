from graph_db import get_graph
import sys


def trace_impact(changed_id, max_depth=5):
    graph = get_graph()

    # Find functions that call the changed function,
    # directly or through other functions.
    query = """
    MATCH p = (affected:Function)-[:CALLS*1..5]->
              (changed:Function {id: $changed_id})
    RETURN affected.id, affected.name, length(p) AS hops
    ORDER BY hops
    """

    result = graph.query(query, {"changed_id": changed_id})

    # Keep the shortest discovered dependency distance for each function.
    impacted = {}

    for function_id, name, hops in result.result_set:
        if function_id not in impacted or hops < impacted[function_id]["hops"]:
            impacted[function_id] = {
                "name": name,
                "hops": hops,
            }

    # Find test functions that depend on the changed function.
    test_query = """
    MATCH p = (test:Function)-[:CALLS*1..5]->
              (changed:Function {id: $changed_id})
    WHERE test.name STARTS WITH 'test_'
    RETURN test.id, length(p) AS hops
    ORDER BY hops
    """

    test_result = graph.query(
        test_query, {"changed_id": changed_id}
    )

    tests = {}
    for test_id, hops in test_result.result_set:
        if test_id not in tests or hops < tests[test_id]:
            tests[test_id] = hops

    print(f"\nChanged function: {changed_id}")

    print("\nPotentially affected functions:")
    if impacted:
        for function_id, details in sorted(
            impacted.items(), key=lambda item: item[1]["hops"]
        ):
            print(
                f"  {function_id} "
                f"(dependency distance: {details['hops']})"
            )
    else:
        print("  No callers found in the graph.")

    print("\nRecommended tests:")
    if tests:
        for test_id in sorted(tests, key=tests.get):
            print(f"  {test_id} (dependency distance: {tests[test_id]})")
    else:
        print("  No connected test functions found.")

    return impacted, tests


if __name__ == "__main__":
    changed_id = (
        sys.argv[1] if len(sys.argv) > 1 else "shop:calculate_tax"
    )
    trace_impact(changed_id)