
try:
    from .graph_db import get_graph
except ImportError:
    from graph_db import get_graph

import sys


def trace_impact(changed_id, max_depth=5):
    graph = get_graph()
    max_depth = max(1, min(max_depth, 10))

    # 1. Find functions that call the changed function.
    query = f"""
    MATCH p = (affected:Function)-[:CALLS*1..{max_depth}]->
              (changed:Function {{id: $changed_id}})
    RETURN affected.id, affected.name, length(p) AS hops
    ORDER BY hops
    """

    result = graph.query(query, {"changed_id": changed_id})
    impacted = {}

    for function_id, name, hops in result.result_set:
        if (
            function_id not in impacted
            or hops < impacted[function_id]["hops"]
        ):
            impacted[function_id] = {
                "name": name,
                "hops": hops,
            }

    # 2. Find connected test functions.
    test_query = f"""
    MATCH p = (test:Function)-[:CALLS*1..{max_depth}]->
              (changed:Function {{id: $changed_id}})
    WHERE test.name STARTS WITH 'test_'
    RETURN test.id, length(p) AS hops
    ORDER BY hops
    """

    test_result = graph.query(
        test_query,
        {"changed_id": changed_id},
    )
    tests = {}

    for test_id, hops in test_result.result_set:
        if test_id not in tests or hops < tests[test_id]:
            tests[test_id] = hops

    # 3. Find the module of the changed function.
    function_result = graph.query(
        """
        MATCH (f:Function {id: $changed_id})
        RETURN f.module
        LIMIT 1
        """,
        {"changed_id": changed_id},
    )

    changed_module = (
        function_result.result_set[0][0]
        if function_result.result_set
        else None
    )

    historical_files = {}
    changed_file = None

    # 4. Match the module to a File node.
    if changed_module:
        module_path = changed_module.replace(".", "/")

        possible_paths = [
            module_path + ".py",
            "src/" + module_path + ".py",
        ]

        if module_path.endswith("/__init__"):
            possible_paths.extend([
                module_path[:-9] + "__init__.py",
                "src/" + module_path[:-9] + "__init__.py",
            ])

        for path in dict.fromkeys(possible_paths):
            path_result = graph.query(
                """
                MATCH (f:File {path: $path})
                RETURN f.path
                LIMIT 1
                """,
                {"path": path},
            )

            if path_result.result_set:
                changed_file = path_result.result_set[0][0]
                break

    # 5. Find historically co-changed files.
    if changed_file:
        cochange_query = """
        MATCH (a:File)-[r:CO_CHANGED]-(b:File)
        WHERE a.path = $path
        RETURN b.path, r.count
        ORDER BY r.count DESC
        LIMIT 10
        """

        cochange_result = graph.query(
            cochange_query,
            {"path": changed_file},
        )

        for file_path, count in cochange_result.result_set:
            if file_path is not None:
                historical_files[file_path] = count

    # 6. Print the impact report.
    print(f"\nChanged function: {changed_id}")

    print("\nPotentially affected functions:")
    if impacted:
        for function_id, details in sorted(
            impacted.items(),
            key=lambda item: item[1]["hops"],
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
            print(
                f"  {test_id} "
                f"(dependency distance: {tests[test_id]})"
            )
    else:
        print("  No connected test functions found.")

    print("\nHistorically co-changed files:")
    if historical_files:
        for file_path, count in historical_files.items():
            print(
                f"  {file_path} "
                f"(changed together {count} times)"
            )
    elif changed_file:
        print(
            f"  No historical relationships found for {changed_file}."
        )
    elif changed_module:
        print(
            f"  Could not match module '{changed_module}' "
            "to a File node in the co-change graph."
        )
    else:
        print("  Could not find the changed function in the graph.")

    return impacted, tests, historical_files


if __name__ == "__main__":
    changed_id = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "shop:calculate_tax"
    )
    trace_impact(changed_id)
