# ChangeImpact AI

**Graph-powered code-change impact analysis with FalkorDB, historical co-change insights, an MCP tool server, and an integrated voice-input assistant.**

ChangeImpact AI helps developers understand which functions may be affected by a code change and identify tests or files worth reviewing before release. It combines a function dependency graph with historical file co-change information. The results are decision-support signals, not guarantees that a particular test will fail.

## Features

- **Repository scan:** parses Python source files and extracts modules, functions, methods, and import information.
- **Dependency graph:** stores function nodes and call relationships in FalkorDB.
- **Change impact analysis:** traces callers and potentially affected functions from a selected function.
- **Historical co-changes:** surfaces files that have changed together in available Git history.
- **Main dashboard:** displays graph metrics, repository scan details, function selection, impact reports, and the voice assistant in one Streamlit app.
- **MCP server:** exposes function search, impact analysis, and historical co-change tools over MCP Streamable HTTP.
- **Voice input:** lets a user speak a request in the main dashboard; speech is transcribed in the browser and sent to the MCP tools. Browser microphone permission is required.

## Architecture

```text
User (text or microphone)
          |
          v
Streamlit main dashboard (app/dashboard1.py)
          |                         
          | direct graph queries     | MCP client (voice panel)
          v                         v
FalkorDB graph  <-------------  MCP server (app/mcp_server.py)
          ^                         |
          +---- indexed repository -+
```

The main dashboard's graph-backed panels use the project's graph connection and analysis modules. The integrated voice panel sends requests to the MCP server at `http://127.0.0.1:8000/mcp`. Keep the MCP server running when using that panel.

## Tech stack

- Python 3.11 (recommended to match the existing project environment)
- Streamlit
- FalkorDB / Redis protocol
- Docker
- MCP Python SDK (Streamable HTTP client/server)
- `streamlit-mic-recorder` for browser speech input
- Python AST-based repository analysis

## Project structure

```text
changeimpact-ai/
├── app/
│   ├── dashboard1.py       # Main dashboard with integrated voice assistant
│   ├── mcp_server.py       # MCP server entry point
│   ├── graph_db.py         # FalkorDB connection helper
│   ├── ast_parser.py       # Python repository scanner
│   ├── build_graph.py      # Graph construction (if present in your checkout)
│   ├── impact_analysis.py  # Dependency impact traversal
│   └── cochange.py         # Historical co-change analysis (if present)
├── data/
│   └── target_repo/        # Repository being analyzed (local data; may be git-ignored)
├── requirements.txt        # Python dependencies (if maintained in this checkout)
└── README.md
```

Keep the existing project files and paths from your repository. Some optional filenames may differ by branch/version.

## Prerequisites

1. Windows 10/11, macOS, or Linux.
2. Python 3.11 recommended.
3. Docker Desktop (or Docker Engine) running.
4. A FalkorDB container named `changeimpact-falkordb`, with the graph data loaded.
5. The repository's Python dependencies installed in a virtual environment.
6. A browser microphone, if using voice input.

## Setup on Windows (PowerShell)

Open a terminal in the repository root.

### 1. Create and activate a virtual environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If `.venv` already exists and works for this project, reuse it rather than recreating it.

### 2. Install dependencies

If your repository contains `requirements.txt`:

```powershell
python -m pip install -r requirements.txt
```

Ensure the environment has the packages used by the app and MCP server. If needed, install the relevant packages with:

```powershell
python -m pip install streamlit pandas falkordb mcp streamlit-mic-recorder
```

Use the project's existing pinned versions if a requirements file already specifies them.

### 3. Start FalkorDB

If your existing container is already created:

```powershell
docker start changeimpact-falkordb
docker exec -it changeimpact-falkordb redis-cli PING
```

The ping should return `PONG`. If the container does not exist, create/start FalkorDB according to the project's existing Docker configuration; do not create a second container without checking the current graph setup.

### 4. Start the MCP server

In **Terminal 1**, from the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
python -m app.mcp_server
```

The server should expose the Streamable HTTP MCP endpoint expected by the client:

```text
http://127.0.0.1:8000/mcp
```

Leave this terminal running. If your server prints a different host or port, update `MCP_URL` in the dashboard to match.

### 5. Start the main dashboard

In **Terminal 2**, from the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
python -m streamlit run app/dashboard1.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.

> Copy the provided integrated dashboard code into `app/dashboard1.py` only after backing up your original file. The downloadable file in this package is named `dashboard1_voice.py` to make that change explicit; rename it to `dashboard1.py` inside your project's `app` directory when ready.

## Using the dashboard

1. **Home / Overview:** verify FalkorDB is connected and inspect function, call, and co-change counts.
2. **Ask ChangeImpact:** enter a function name or question and run impact analysis.
3. **Choose a function manually:** use the function selector when natural-language matching is ambiguous.
4. **Impact Report:** review affected functions and recommended/connected test candidates.
5. **Repository scan details:** review scan statistics for the target repository.
6. **Voice assistant:** type a request or choose **Start speaking**. Allow microphone access in the browser. Example requests:
   - `Find the function prepare_body`
   - `Analyze the impact of src.requests.models:_encode_files`
   - `Find files historically changed with src/requests/models.py`

The voice panel currently provides speech-to-text input and displays text responses; it does not synthesize spoken audio replies.

## MCP tools

The MCP server is intended to expose these tools:

- `search_functions(search_term, limit=10)` — search indexed function records.
- `analyze_change_impact(changed_function_id, max_depth=5)` — trace potentially affected functions.
- `get_historical_cochanges(file_path, limit=10)` — retrieve historical co-change information for a file.

Use the MCP server's actual tool schema as the source of truth if names or parameters have changed in your branch.

## Troubleshooting

### FalkorDB connection error

- Check Docker Desktop is running.
- Run `docker start changeimpact-falkordb`.
- Confirm `PING` returns `PONG`.
- Verify the graph connection settings in `app/graph_db.py`.

### MCP connection or tool error

- Confirm `python -m app.mcp_server` is still running.
- Confirm the endpoint is `http://127.0.0.1:8000/mcp` and update `MCP_URL` if needed.
- Check that the MCP server uses the same FalkorDB graph as the main dashboard.

### Microphone button missing or not working

- Install `streamlit-mic-recorder` in the same `.venv` used to run Streamlit.
- Open the dashboard in a browser and allow microphone access for `localhost`.
- Refresh the page after changing browser permissions.
- Check browser/device microphone settings.

### No functions or impact results

- Confirm the repository has been scanned and the graph populated.
- Check that the selected function ID exists in the graph.
- Use the manual function selector or provide a full function ID to avoid ambiguous matches.

## Limitations and responsible interpretation

- Impact analysis depends on the completeness of the indexed code and call graph. Dynamic calls, reflection, generated code, and missing edges may not be captured.
- Recommended tests are candidates for review, not proof of test coverage or guaranteed failure detection.
- Historical co-change links show correlation in version history, not causation.
- Voice recognition depends on browser permissions, microphone quality, and speech-recognition support.
- The integrated dashboard and MCP endpoint are local-development defaults; public deployment requires separate hosting, network configuration, and secret management.

## Demo checklist

- [ ] Start FalkorDB and confirm `PONG`.
- [ ] Start the MCP server and confirm the tools are available.
- [ ] Launch the main dashboard.
- [ ] Show the overview metrics.
- [ ] Run one impact-analysis example and show affected functions/tests.
- [ ] Demonstrate a voice request with microphone permission enabled.
- [ ] Show a historical co-change query.
- [ ] Explain that impact/test suggestions are candidates and co-change is correlation.

## Acknowledgements

Built as a graph-based developer-intelligence project using FalkorDB, Python, Streamlit, and the Model Context Protocol (MCP).
