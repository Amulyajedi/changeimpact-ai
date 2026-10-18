# ChangeImpact AI

**Graph-based code impact analysis using Python, FalkorDB, and Git history.**

ChangeImpact AI helps developers understand what code may be affected when a function changes. It analyzes function dependencies and historical file co-changes to identify potentially affected functions and relevant files before testing.

## Features

- Extracts Python functions and methods using AST parsing.
- Traces potentially affected functions through a dependency graph.
- Searches for connected test functions.
- Uses Git history to identify files that have historically changed together.
- Displays analysis results in a dark Streamlit dashboard.
- Shows graph statistics and historical co-change frequencies.

## How It Works

1. **Parse code:** Extract functions and call information from the target Python repository.
2. **Build a graph:** Store functions and `CALLS` relationships in FalkorDB.
3. **Analyze Git history:** Store historical file relationships using `CO_CHANGED` edges.
4. **Trace impact:** Find callers of the selected function within a configurable dependency depth.
5. **Display results:** Present potentially affected functions, connected tests, and historical co-changes.

## Graph Data Model

- `(:Function)` — represents a function or method. Properties include `id`, `name`, and `module`.
- `(:Function)-[:CALLS]->(:Function)` — represents a recorded call relationship.
- `(:File)` — represents a source file, identified by its `path`.
- `(:File)-[:CO_CHANGED {count: N}]-(:File)` — represents files changed together in Git history. `count` stores the co-change frequency.

## Cypher Queries

### Count functions

```cypher
MATCH (f:Function)
RETURN count(f)
```

### Count call relationships

```cypher
MATCH ()-[r:CALLS]->()
RETURN count(r)
```

### Trace potentially affected functions

```cypher
MATCH p = (affected:Function)-[:CALLS*1..5]->
          (changed:Function {id: $changed_id})
RETURN affected.id, affected.name, length(p) AS hops
ORDER BY hops
```

### Retrieve historical co-changes

```cypher
MATCH (a:File)-[r:CO_CHANGED]-(b:File)
WHERE a.path = $path
RETURN b.path, r.count
ORDER BY r.count DESC
LIMIT 10
```

## Technology Stack

- Python
- Streamlit
- FalkorDB
- Git
- Python AST parsing
- Cypher graph queries
- Pandas

## Local Setup

### 1. Clone the repository

```powershell
git clone YOUR_PUBLIC_REPOSITORY_URL
cd changeimpact-ai
```

Replace the placeholder with your actual public GitHub repository URL.

### 2. Create a virtual environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 3. Install dependencies

If the repository contains `requirements.txt`:

```powershell
pip install -r requirements.txt
```

Otherwise, install the required packages and any other dependencies used by your code:

```powershell
pip install streamlit pandas falkordb
```

### 4. Start FalkorDB

Start your existing FalkorDB Docker container. For a fresh local instance, you can use:

```powershell
docker run -d --name changeimpact-falkordb -p 6379:6379 -p 3000:3000 falkordb/falkordb:latest
```

If the container already exists, start it instead:

```powershell
docker start changeimpact-falkordb
```

The application connects to `localhost:6379` and uses the `ChangeImpact` graph.

### 5. Prepare graph data

Follow the instructions in the repository's graph-building and Git-history scripts, including `app/build_graph.py` and `app/cochange.py`, to populate the graph before running the analysis.

Avoid rebuilding or importing data unnecessarily if your graph is already populated.

### 6. Run the dashboard

From the project root, run the command matching your dashboard's actual location. For example:

```powershell
python -m streamlit run dashboard\app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.

## Example Analysis

For the function `src.requests.models:_encode_files`, the current graph identified:

- `src.requests.models:prepare_body` — dependency distance 1.
- `src.requests.models:prepare` — dependency distance 2.

Historical co-change results included:

- `src/requests/__init__.py` — 6 times.
- `tests/test_requests.py` — 5 times.
- `pyproject.toml` — 5 times.

These results illustrate how dependency relationships and Git history can provide complementary signals during code-change review.

## Limitations

- Static analysis may miss dynamic calls, reflection, and unresolved dependencies.
- Test recommendations depend on test functions being connected in the recorded call graph.
- Historical co-changes indicate patterns in prior commits, not guaranteed dependencies.
- Results depend on the quality and completeness of the graph data.

## License

MIT — see the `LICENSE` file.
