
import itertools
import subprocess
import sys
from collections import Counter
from pathlib import Path

from graph_db import get_graph


def mine_cochanges(repo_path):
    """Count how often pairs of files change in the same commit."""
    repo = Path(repo_path).resolve()

    result = subprocess.run(
        [
            "git", "-C", str(repo),
            "log", "--no-merges",
            "--format=%x1e%H", "--name-only",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    pair_counts = Counter()
    commit_count = 0

    for record in result.stdout.split("\x1e"):
        lines = record.strip().splitlines()
        if not lines:
            continue

        # The first line is the commit hash.
        files = sorted(set(line.strip() for line in lines[1:] if line.strip()))
        if len(files) < 2:
            continue

        commit_count += 1

        for file_a, file_b in itertools.combinations(files, 2):
            pair_counts[(file_a, file_b)] += 1

    return commit_count, pair_counts


def store_cochanges(pair_counts):
    """Store file pairs without deleting existing function nodes or edges."""
    graph = get_graph()

    for (file_a, file_b), count in pair_counts.items():
        graph.query(
            """
            MERGE (a:File {path: $file_a})
            MERGE (b:File {path: $file_b})
            MERGE (a)-[r:CO_CHANGED]->(b)
            SET r.count = $count
            """,
            {
                "file_a": file_a,
                "file_b": file_b,
                "count": count,
            },
        )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python app/cochange.py <git-repository-path>")
        sys.exit(1)

    try:
        commits, pairs = mine_cochanges(sys.argv[1])
        store_cochanges(pairs)

        print(f"Commits with multiple changed files: {commits}")
        print(f"Unique file pairs found: {len(pairs)}")
        print("\nMost frequent co-change pairs:")

        for (file_a, file_b), count in pairs.most_common(10):
            print(f"{count} | {file_a} <-> {file_b}")

        print("\nCo-change relationships stored in FalkorDB.")
    except (subprocess.CalledProcessError, FileNotFoundError) as error:
        print(f"Could not analyse repository: {error}")
        sys.exit(1)
