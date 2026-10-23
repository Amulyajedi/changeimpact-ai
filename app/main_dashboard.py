import contextlib
import asyncio
import json
import re
from typing import Any
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from streamlit_mic_recorder import speech_to_text

MCP_URL = "http://127.0.0.1:8000/mcp"
import io
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# ------------------------------------------------------------
# Paths and imports
# ------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"
TARGET_REPO = ROOT / "data" / "target_repo"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from graph_db import get_graph
from impact_analysis import trace_impact
from ast_parser import scan_project

st.set_page_config(
    page_title="ChangeImpact AI | Code Risk Intelligence",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
    :root { --bg:#090D16; --border:rgba(148,163,184,.18); --text:#F4F7FB; --muted:#9AA9BE; --cyan:#62E6D5; --blue:#7AA8FF; --purple:#B6A0FF; }
    html, body, [class*="css"] { font-family:'Manrope',sans-serif; }
    .stApp {
      background:radial-gradient(ellipse at 12% 0%,rgba(56,96,180,.20),transparent 34%),
                 radial-gradient(ellipse at 92% 8%,rgba(53,211,190,.10),transparent 28%),var(--bg);
      color:var(--text);
    }
    [data-testid="stHeader"] { background:rgba(9,13,22,.72); }
    [data-testid="stSidebar"] { background:linear-gradient(180deg,#101827 0%,#0C1220 100%); border-right:1px solid var(--border); }
    [data-testid="stSidebar"] * { color:#EAF0FA; }
    .block-container { max-width:1500px; padding-top:1.6rem; padding-bottom:3rem; }
    h1,h2,h3 { letter-spacing:-.035em; } h1 { font-weight:800!important; }
    .hero {
      padding:30px 32px; border:1px solid rgba(122,168,255,.28); border-radius:24px;
      background:radial-gradient(circle at 88% 16%,rgba(98,230,213,.18),transparent 25%),
      linear-gradient(120deg,rgba(25,36,58,.98),rgba(17,24,39,.96) 58%,rgba(24,31,57,.98));
      box-shadow:0 20px 70px rgba(0,0,0,.22); margin-bottom:22px;
    }
    .eyebrow { color:var(--cyan); text-transform:uppercase; letter-spacing:.16em; font:600 11px 'DM Mono',monospace; margin-bottom:10px; }
    .hero h1 { font-size:clamp(2rem,4vw,3.15rem); margin:0 0 8px 0; color:#F8FAFF; }
    .hero p { max-width:720px; color:#B6C4D9; font-size:1rem; line-height:1.65; margin:0; }
    .hero-pill { display:inline-block; margin-top:18px; padding:7px 11px; border-radius:999px; border:1px solid rgba(98,230,213,.3); background:rgba(98,230,213,.08); color:#9AF4E8; font:500 11px 'DM Mono',monospace; }
    .section-kicker { color:var(--cyan); text-transform:uppercase; letter-spacing:.13em; font:500 10px 'DM Mono',monospace; margin-bottom:5px; }
    .section-title { color:#F4F7FB; font-size:1.45rem; font-weight:800; letter-spacing:-.03em; }
    .section-subtitle { color:var(--muted); font-size:.9rem; margin-top:2px; margin-bottom:15px; }
    .glass-card { background:linear-gradient(145deg,rgba(21,30,46,.94),rgba(14,21,34,.96)); border:1px solid var(--border); border-radius:18px; padding:18px 20px; height:100%; }
    .metric-label { color:#9AA9BE; font-size:.77rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; }
    .metric-value { color:#F7FAFF; font-size:1.8rem; font-weight:800; line-height:1.25; margin-top:7px; }
    .metric-foot { color:#8494AB; font-size:.76rem; margin-top:5px; }
    .status-dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:#62E6D5; margin-right:7px; box-shadow:0 0 10px rgba(98,230,213,.7); }
    .code-chip { display:inline-block; background:rgba(122,168,255,.10); color:#C9DAFF; border:1px solid rgba(122,168,255,.24); border-radius:8px; padding:5px 8px; font:500 12px 'DM Mono',monospace; overflow-wrap:anywhere; }
    .insight { border-left:3px solid var(--cyan); background:rgba(98,230,213,.06); border-radius:0 12px 12px 0; padding:13px 15px; color:#D9E8F2; margin:8px 0 12px; }
    .small-muted { color:var(--muted); font-size:.82rem; }
    div[data-testid="stMetric"] { background:linear-gradient(145deg,#151F30,#101725); border:1px solid var(--border); padding:16px 18px; border-radius:16px; box-shadow:0 8px 24px rgba(0,0,0,.12); }
    div[data-testid="stMetricLabel"] { color:#A8B7CB; } div[data-testid="stMetricValue"] { color:#F5F8FF; }
    div[data-testid="stDataFrame"] { border:1px solid var(--border); border-radius:12px; overflow:hidden; }
    .stButton>button,.stFormSubmitButton>button { border-radius:11px; font-weight:700; min-height:2.8rem; border:1px solid rgba(98,230,213,.35); transition:all .15s ease; }
    .stButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"] { background:linear-gradient(100deg,#62E6D5,#7AA8FF); color:#07111B; border:0; }
    .stButton>button:hover,.stFormSubmitButton>button:hover { transform:translateY(-1px); border-color:var(--cyan); }
    div[data-baseweb="select"]>div,div[data-baseweb="input"]>div,div[data-baseweb="textarea"]>div { background-color:#111A29; border-color:#2C3A50; border-radius:10px; }
    .nav-label { color:var(--cyan); text-transform:uppercase; letter-spacing:.13em; font:500 10px 'DM Mono',monospace; margin:4px 0 10px; }
    .side-nav { display:flex; flex-direction:column; gap:7px; }
    .side-nav a { display:flex; align-items:center; gap:11px; padding:11px 12px; border-radius:11px; text-decoration:none !important; color:#DDE7F6 !important; border:1px solid transparent; background:rgba(255,255,255,.025); font-size:13px; font-weight:650; transition:all .15s ease; }
    .side-nav a span { display:inline-flex; align-items:center; justify-content:center; width:23px; height:23px; border-radius:7px; color:var(--cyan); background:rgba(98,230,213,.09); font-size:15px; }
    .side-nav a:hover { background:rgba(98,230,213,.08); border-color:rgba(98,230,213,.28); color:#FFFFFF !important; }
    hr { border-color:var(--border); }
    .footer { color:#718198; font:11px 'DM Mono',monospace; text-align:center; padding-top:20px; }
    </style>
    """,
    unsafe_allow_html=True,
)



# MCP voice assistant state and helper functions
for _key, _default in (("voice_messages", []), ("voice_counter", 0)):
    if _key not in st.session_state:
        st.session_state[_key] = _default

def extract_result(result: Any) -> Any:
    values = []
    for item in getattr(result, "content", []) or []:
        if hasattr(item, "text"):
            try:
                values.append(json.loads(item.text))
            except (json.JSONDecodeError, TypeError):
                values.append(item.text)
    if getattr(result, "isError", False):
        return {"error": values or ["MCP tool execution failed."]}
    if len(values) == 1:
        return values[0]
    return values


async def call_tool_async(tool_name: str, arguments: dict) -> Any:
    async with streamablehttp_client(MCP_URL) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return extract_result(result)


def run_tool(tool_name: str, arguments: dict) -> Any:
    try:
        return asyncio.run(call_tool_async(tool_name, arguments))
    except Exception as exc:
        return {"error": str(exc), "hint": f"Start FalkorDB and the MCP server. Expected MCP URL: {MCP_URL}"}


def understand_request(user_text: str):
    message = re.sub(r"\s+", " ", user_text.strip())
    lower = message.lower()
    if not message:
        return "help", None, "Please enter a request."

    if any(p in lower for p in ("historical co-change", "historical cochange", "changed together", "co-changed", "cochanged", "files changed with", "co-change", "historically changed with")):
        match = re.search(r"[\w./\\-]+\.py\b", message, re.I)
        if not match:
            return "help", None, "Please include a repository-relative Python file path, e.g. src/requests/models.py."
        path = match.group(0).replace("\\", "/").removeprefix("./")
        return "historical", {"file_path": path, "limit": 10}, f"I'll retrieve historical co-changes for `{path}`."

    if re.search(r"\b(hello|hi|hey)\b", lower) or "what can you do" in lower or lower == "help":
        return "help", None, "I'm ChangeImpact Voice. I can search functions, analyze potential change impact, and retrieve historical co-changes."

    is_impact = any(p in lower for p in ("impact", "affected", "break", "dependency", "dependencies", "tests should", "test should", "analyze change", "analyse change", "what happens if", "what might break", "test recommendations", "analyze", "analyse"))
    if is_impact:
        # Match full qualified graph IDs such as src.requests.models:_encode_files.
        exact_id = re.search(r"([A-Za-z0-9_./<>-]+\s*:\s*[A-Za-z0-9_./<>-]+)", message)
        if exact_id:
            function_id = re.sub(r"\s*:\s*", ":", exact_id.group(1)).rstrip(".,?!")
            return "impact", {"changed_function_id": function_id, "max_depth": 5}, f"I'll analyze the potential impact of `{function_id}`."
        cleaned = re.sub(r"[’']s\b", "", message, flags=re.I)
        # Preserve the function phrase, but discard conversational filler and module words.
        cleaned = re.sub(r"[.:/\\]+", " ", cleaned)
        cleaned = re.sub(r"\b(src|requests?|models?|module|file|files|function|functions|the|a|an|of|for|please|code|change|impact|analyse|analyze|on|to|me|what|is|are|should|could|might|happen|if|test|tests|recommendations?|in|give|show|find|search|can|you|tell|about)\b", " ", cleaned, flags=re.I)
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9_]*", cleaned)
        if tokens:
            # Speech often separates snake_case names: "prepare body" -> "prepare_body".
            term = "_".join(tokens[-3:]).strip("_")
            return "impact_search", {"search_term": term, "limit": 10}, f"I'll find `{term}` and analyze its potential impact."
        return "help", None, "Please name a function, e.g. `Analyze the impact of prepare_body`, or use a complete ID such as `src.requests.models:_encode_files`. A module alone is not a function to analyze."

    if any(p in lower for p in ("search", "find", "look for", "where is", "show functions", "function named")):
        term = message
        term = re.sub(r"^(please\s+)?(search|find|look for|show)\s+", "", term, flags=re.I)
        term = re.sub(r"^(the\s+)?functions?\b\s*[:=-]?\s*", "", term, flags=re.I)
        term = re.sub(r"^(a|the)\s+", "", term, flags=re.I)
        term = re.sub(r"\b(function|named|called|please)\b", " ", term, flags=re.I)
        term = term.strip().strip(" :.,!?;\"'`")
        term = re.sub(r"^[^A-Za-z0-9_]+|[^A-Za-z0-9_]+$", "", term).strip()
        # Normalize spoken snake_case names such as "prepare body".
        if " " in term and not any(ch in term for ch in ".:/"):
            term = "_".join(term.split())
        if term:
            return "search", {"search_term": term, "limit": 10}, f"I'll search the dependency graph for `{term}`."
        return "help", None, "Please enter a function name or module to search."

    return "help", None, "Try: `Find prepare_body`, `Analyze the impact of src.requests.models:_encode_files`, or `Find files historically changed with src/requests/models.py`."


def function_records(search_result: Any) -> list[dict]:
    if isinstance(search_result, list):
        records = search_result
    elif isinstance(search_result, dict):
        records = search_result.get("functions") or search_result.get("results") or search_result.get("matches")
        if records is None and isinstance(search_result.get("data"), (dict, list)):
            data = search_result["data"]
            records = data if isinstance(data, list) else (data.get("functions") or data.get("results") or data.get("matches"))
    else:
        records = []
    if isinstance(records, dict):
        records = list(records.values())
    return [x for x in records if isinstance(x, dict)] if isinstance(records, list) else []


def function_id(record: dict):
    for key in ("id", "function_id", "qualified_name", "full_name"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def process_request(user_text: str) -> dict:
    intent, arguments, intro = understand_request(user_text)
    if intent == "help":
        return {"message": intro, "tool": None, "result": None}
    tool_map = {"search": "search_functions", "impact": "analyze_change_impact", "historical": "get_historical_cochanges", "impact_search": "search_functions"}
    tool_name = tool_map[intent]
    result = run_tool(tool_name, arguments)
    if intent != "impact_search":
        return {"message": intro, "tool": tool_name, "result": result}
    if isinstance(result, dict) and result.get("error"):
        return {"message": "Function search failed, so impact analysis could not run. Check the MCP server connection.", "tool": "search_functions", "result": result}
    functions = function_records(result)
    term = str(arguments.get("search_term", "")).strip().lower()
    exact = [item for item in functions if str(item.get("name", "")).strip().lower() == term or str(function_id(item) or "").strip().lower() == term]
    partial = [item for item in functions if term and (term in str(item.get("name", "")).lower() or term in str(function_id(item) or "").lower())]
    if len(exact) == 1:
        chosen = exact[0]
    elif len(partial) == 1:
        chosen = partial[0]
    elif len(functions) == 1:
        chosen = functions[0]
    else:
        return {"message": f"Found {len(functions)} possible match(es) for `{arguments.get('search_term', '')}`, but couldn't identify one unique function. Try the complete function ID, e.g. `src.requests.models:_encode_files`.", "tool": "search_functions", "result": result}
    fid = function_id(chosen)
    if not fid:
        return {"message": "The search result did not include a usable function ID, so impact analysis could not run.", "tool": "search_functions", "result": result}
    impact_result = run_tool("analyze_change_impact", {"changed_function_id": fid, "max_depth": 5})
    return {"message": f"Found `{fid}` and ran impact analysis.", "tool": "analyze_change_impact", "result": impact_result}


def submit_request(user_text: str):
    if not user_text or not user_text.strip():
        return
    clean = user_text.strip()
    st.session_state.messages.append({"role": "user", "content": clean})
    st.session_state.messages.append({"role": "assistant", "content": process_request(clean)})


def render_impact_result(result: Any):
    """Render readable impact output when backend returns structured data; retain raw result for debugging."""
    if isinstance(result, dict) and result.get("error"):
        st.error("Impact analysis failed. Check the MCP server and graph database.")
        st.json(result)
        return
    if not isinstance(result, dict):
        st.info("The MCP server returned a non-dictionary result. Raw response:")
        st.json(result)
        return

    # Different server versions may use different key names. Recognize common forms.
    impacted = result.get("impacted") or result.get("affected_functions") or result.get("potentially_affected") or result.get("affected")
    tests = result.get("tests") or result.get("recommended_tests") or result.get("test_recommendations")
    changed = result.get("changed_function") or result.get("changed_function_id") or result.get("function_id")
    if changed:
        st.markdown(f"**Changed function:** `{changed}`")
    if isinstance(impacted, dict):
        st.metric("Potentially affected functions", len(impacted))
        rows = []
        for fid, details in impacted.items():
            if isinstance(details, dict):
                rows.append({"Function": details.get("name") or fid, "Function ID": fid, "Dependency distance": details.get("hops", details.get("distance", details.get("depth", "")))})
            else:
                rows.append({"Function": str(fid), "Function ID": str(fid), "Dependency distance": details})
        if rows:
            st.subheader("Potentially affected functions")
            st.dataframe(rows, use_container_width=True, hide_index=True)
    elif isinstance(impacted, list):
        st.metric("Potentially affected functions", len(impacted))
        st.subheader("Potentially affected functions")
        st.dataframe(impacted, use_container_width=True, hide_index=True)
    if isinstance(tests, (dict, list)) and tests:
        st.subheader("Recommended / connected tests")
        if isinstance(tests, dict):
            st.dataframe([{"Test": k, "Details": v} for k, v in tests.items()], use_container_width=True, hide_index=True)
        else:
            st.dataframe(tests, use_container_width=True, hide_index=True)
    # Keep the actual response visible; useful when the backend schema differs.
    with st.expander("Raw MCP response (debugging)"):
        st.json(result)



def section_heading(kicker, title, subtitle=""):
    st.markdown(
        f'<div class="section-kicker">{kicker}</div><div class="section-title">{title}</div><div class="section-subtitle">{subtitle}</div>',
        unsafe_allow_html=True,
    )


def load_function_options(graph):
    result = graph.query("""
        MATCH (f:Function)
        RETURN f.id, f.name, f.module
        ORDER BY f.module, f.name
    """)
    unique = {}
    for row in result.result_set or []:
        function_id, name, module = row
        if function_id:
            unique[str(function_id)] = {
                "id": str(function_id),
                "name": str(name or function_id),
                "module": str(module or ""),
            }
    return list(unique.values())


def run_analysis(function_id, depth):
    captured_output = io.StringIO()
    with contextlib.redirect_stdout(captured_output):
        impacted, tests, historical_files = trace_impact(function_id, max_depth=depth)
    st.session_state["impact_results"] = {
        "selected_id": function_id,
        "impacted": impacted or {},
        "tests": tests or {},
        "historical_files": historical_files or {},
        "max_depth": depth,
    }


def match_function(question, options):
    q = question.casefold()
    matches = [
        item for item in options
        if item["id"].casefold() in q or item["name"].casefold() in q
    ]
    if not matches:
        return None
    matches.sort(key=lambda item: max(len(item["id"]), len(item["name"])), reverse=True)
    return matches[0]


def render_results(results):
    function_id = results["selected_id"]
    impacted, tests, historical_files = results["impacted"], results["tests"], results["historical_files"]
    st.markdown(f'<div class="code-chip">CHANGE TARGET · {function_id}</div>', unsafe_allow_html=True)
    st.write("")
    a, b, c = st.columns(3)
    a.metric("Potentially affected", len(impacted))
    b.metric("Connected tests found", len(tests))
    c.metric("Historical related files", len(historical_files))

    impact_rows = [
        {"Function": details.get("name", fid), "Function ID": fid, "Dependency distance": details.get("hops", "")}
        for fid, details in impacted.items()
    ]
    impact_df = pd.DataFrame(impact_rows)
    if not impact_df.empty:
        impact_df["Dependency distance"] = pd.to_numeric(impact_df["Dependency distance"], errors="coerce")
        impact_df = impact_df.sort_values("Dependency distance", kind="stable")

    tab_impact, tab_tests, tab_history = st.tabs(["🔗 Impacted functions", "🧪 Connected tests", "📜 Git co-changes"])
    with tab_impact:
        if not impact_df.empty:
            st.dataframe(impact_df, use_container_width=True, hide_index=True)
            chart_df = impact_df.dropna(subset=["Dependency distance"])
            if not chart_df.empty:
                st.caption("Dependency distance — smaller values are closer to the changed function.")
                st.bar_chart(chart_df.set_index("Function")["Dependency distance"], color="#62E6D5")
        else:
            st.info("No callers were found in the current graph within this search depth.")
    with tab_tests:
        if tests:
            test_df = pd.DataFrame([{"Test function ID": tid, "Dependency distance": distance} for tid, distance in tests.items()])
            test_df = test_df.sort_values("Dependency distance", kind="stable")
            st.dataframe(test_df, use_container_width=True, hide_index=True)
        else:
            st.info("No connected test functions were found by this graph query. This does not mean the code is untested; verify test coverage separately.")
    with tab_history:
        if historical_files:
            history_df = pd.DataFrame([{"Related file": path, "Times changed together": count} for path, count in historical_files.items()])
            history_df["Times changed together"] = pd.to_numeric(history_df["Times changed together"], errors="coerce")
            history_df = history_df.sort_values("Times changed together", ascending=False, na_position="last")
            st.dataframe(history_df, use_container_width=True, hide_index=True)
            chart_history = history_df.dropna(subset=["Times changed together"]).head(10)
            if not chart_history.empty:
                st.caption("Most frequent historical co-changes")
                st.bar_chart(chart_history.set_index("Related file")["Times changed together"], color="#B6A0FF")
        else:
            st.info("No historical co-change records were returned. Check the repository's file mapping and available Git history.")
    st.caption("These are graph-based candidates, not proof that a change will cause a failure. Historical co-changes indicate correlation, not causation. Dynamic calls or missing graph edges may not be detected.")


# Sidebar navigation — links jump to sections on this dashboard.
with st.sidebar:
    st.markdown("## 🧭 ChangeImpact")
    st.caption("CODE RISK INTELLIGENCE")
    st.divider()
    st.markdown("<div class='nav-label'>NAVIGATION</div>", unsafe_allow_html=True)
    st.markdown(
        """
        <nav class="side-nav">
          <a href="#overview"><span>⌂</span> Home / Overview</a>
          <a href="#ask-changeimpact"><span>✦</span> Ask ChangeImpact</a>
          <a href="#impact-report"><span>⌁</span> Impact Report</a>
          <a href="#repository-scan"><span>▦</span> Repository Scan</a>
          <a href="#voice-assistant"><span>🎙</span> Voice Assistant</a>
        </nav>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("**TECH STACK**")
    st.markdown("`Python`  `FalkorDB`  `Streamlit`")
    st.caption("MCP tools available separately through app/mcp_server.py")

# Hero / Overview anchor
st.markdown('<div id="overview"></div>', unsafe_allow_html=True)
st.markdown("""
<div class="hero">
  <div class="eyebrow">DEVELOPER INTELLIGENCE · GRAPH-POWERED</div>
  <h1>Know the ripple<br/>before the release.</h1>
  <p>Explore code dependencies, surface potentially affected functions, and discover files that have historically changed together — before you run your tests.</p>
  <div class="hero-pill">✦ CHANGE IMPACT ANALYSIS &nbsp; / &nbsp; DEPENDENCY GRAPH</div>
</div>
""", unsafe_allow_html=True)

# Database connection
graph = None
connection_error = None
try:
    graph = get_graph()
    graph.query("RETURN 1")
except Exception as error:
    connection_error = str(error)

if graph is None:
    st.error("FalkorDB is unavailable. Start your existing FalkorDB container and refresh.")
    if connection_error:
        with st.expander("Connection details"):
            st.code(connection_error)
    st.stop()

try:
    function_options = load_function_options(graph)
except Exception as error:
    st.error(f"Could not load functions from FalkorDB: {error}")
    st.stop()

try:
    function_count_graph = graph.query("MATCH (f:Function) RETURN count(f)").result_set[0][0]
    call_count = graph.query("MATCH ()-[r:CALLS]->() RETURN count(r)").result_set[0][0]
    cochange_count = graph.query("MATCH ()-[r:CO_CHANGED]-() RETURN count(r)").result_set[0][0] // 2
except Exception:
    function_count_graph, call_count, cochange_count = len(function_options), 0, 0

status_left, status_right = st.columns([3, 1])
with status_left:
    st.markdown('<span class="status-dot"></span><span class="small-muted">FALKORDB CONNECTED</span> &nbsp;&nbsp; <span class="small-muted">·&nbsp; Live graph query</span>', unsafe_allow_html=True)
with status_right:
    st.markdown(f'<div style="text-align:right;color:#9AA9BE;font-size:.8rem;">{len(function_options):,} indexed functions</div>', unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Function nodes", f"{function_count_graph:,}")
m2.metric("Call relationships", f"{call_count:,}")
m3.metric("Co-change links", f"{cochange_count:,}")
m4.metric("Repository indexed", "YES" if TARGET_REPO.is_dir() else "CHECK")

st.markdown('<div id="repository-scan"></div>', unsafe_allow_html=True)
with st.expander("Repository scan details", expanded=False):
    if TARGET_REPO.is_dir():
        try:
            with st.spinner("Scanning repository files..."):
                modules = scan_project(str(TARGET_REPO))
            s1, s2, s3 = st.columns(3)
            s1.metric("Python modules", len(modules))
            s2.metric("Functions & methods", sum(len(module.get("functions", [])) for module in modules))
            s3.metric("Import bindings", sum(len(module.get("import_bindings", [])) for module in modules))
        except Exception as error:
            st.warning(f"Repository scan failed: {error}")
    else:
        st.warning(f"Target repository folder not found: {TARGET_REPO}")

st.divider()
st.markdown('<div id="ask-changeimpact"></div>', unsafe_allow_html=True)
section_heading("01 / START AN ANALYSIS", "Ask a question. Trace the impact.", "Try a natural-language question with a function name, or use the full function selector below.")

ask_col, tip_col = st.columns([1.7, 1])
with ask_col:
    with st.form("conversational_analysis", clear_on_submit=False):
        question = st.text_input("Ask ChangeImpact", placeholder="e.g. What could break if I change _encode_files?", label_visibility="collapsed")
        ask_submitted = st.form_submit_button("✦ Find impact", type="primary", use_container_width=True)
with tip_col:
    st.markdown("""
    <div class="glass-card">
      <div class="section-kicker">QUICK TIP</div>
      <div style="font-weight:800;font-size:1rem;margin-bottom:6px;">Be specific</div>
      <div class="small-muted">Include the exact function name in your question. This prototype matches it to the graph before running analysis.</div>
    </div>
    """, unsafe_allow_html=True)

if ask_submitted:
    if not question.strip():
        st.warning("Enter a question first.")
    else:
        matched = match_function(question, function_options)
        if matched:
            st.session_state["selected_function_id"] = matched["id"]
            st.session_state["last_question"] = question
            try:
                with st.spinner(f"Tracing dependencies for {matched['name']}..."):
                    run_analysis(matched["id"], 5)
                st.session_state.pop("question_error", None)
            except Exception as error:
                st.session_state["question_error"] = str(error)
        else:
            st.session_state["question_error"] = "I couldn't match a function in that question. Include its exact name (e.g. _encode_files), or use the selector below."

if st.session_state.get("question_error"):
    st.info(st.session_state["question_error"])

if st.session_state.get("last_question") and st.session_state.get("selected_function_id"):
    st.markdown(f'<div class="insight"><b>Question received:</b> {st.session_state["last_question"]}<br/><span class="small-muted">Matched target: </span><span class="code-chip">{st.session_state["selected_function_id"]}</span></div>', unsafe_allow_html=True)

with st.expander("Or choose a function manually", expanded=not bool(st.session_state.get("selected_function_id"))):
    if function_options:
        option_ids = [item["id"] for item in function_options]
        current = st.session_state.get("selected_function_id")
        default_index = option_ids.index(current) if current in option_ids else 0
        selected_id = st.selectbox(
            "Changed function",
            options=option_ids,
            index=default_index,
            format_func=lambda fid: next((f'{item["name"]} · {item["module"]}' if item["module"] else item["name"] for item in function_options if item["id"] == fid), fid),
            key="manual_function_selector",
        )
        depth = st.slider("Dependency search depth", min_value=1, max_value=10, value=5, help="Maximum CALLS path length to search.")
        if st.button("Analyze selected function", type="primary", use_container_width=True):
            st.session_state["selected_function_id"] = selected_id
            try:
                with st.spinner("Tracing dependencies and retrieving historical co-changes..."):
                    run_analysis(selected_id, depth)
                st.session_state.pop("question_error", None)
                st.session_state.pop("last_question", None)
            except Exception as error:
                st.error(f"Impact analysis failed: {error}")
    else:
        st.warning("No Function nodes were found in FalkorDB.")

st.divider()
st.markdown('<div id="impact-report"></div>', unsafe_allow_html=True)
section_heading("02 / IMPACT REPORT", "Your change, mapped.", "Review graph-connected functions, test candidates, and historical file relationships.")
results = st.session_state.get("impact_results")
if results:
    render_results(results)
else:
    st.markdown("""
    <div class="glass-card">
      <div class="section-kicker">READY WHEN YOU ARE</div>
      <div style="font-size:1.15rem;font-weight:800;margin-bottom:6px;">No analysis run yet</div>
      <div class="small-muted">Ask a question above or select a function manually. Your impact report will appear here.</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()
st.markdown('<div id="voice-assistant"></div>', unsafe_allow_html=True)
section_heading("03 / VOICE ASSISTANT", "Talk to your codebase.", "Use your microphone or type a request. Voice requests are sent to the MCP server and use the same graph-backed tools.")
st.caption("MCP endpoint: http://127.0.0.1:8000/mcp · Start app/mcp_server.py in a separate terminal before using this panel.")

for _item in st.session_state.voice_messages:
    with st.chat_message(_item["role"]):
        _content = _item["content"]
        if _item["role"] == "user":
            st.markdown(_content)
        else:
            st.markdown(_content.get("message", "No response message."))
            if _content.get("tool"):
                st.caption(f"MCP tool executed: `{_content['tool']}`")
            if _content.get("result") is not None:
                render_impact_result(_content["result"])

with st.form("voice_text_form", clear_on_submit=True):
    _voice_text = st.text_input("Ask the MCP assistant", placeholder="Analyze the impact of src.requests.models:_encode_files")
    _voice_send = st.form_submit_button("Send to assistant", type="primary", use_container_width=True)
if _voice_send and _voice_text.strip():
    st.session_state.voice_messages.append({"role": "user", "content": _voice_text.strip()})
    st.session_state.voice_messages.append({"role": "assistant", "content": process_request(_voice_text.strip())})
    st.rerun()

st.markdown("**Or use your microphone**")
try:
    _spoken = speech_to_text(language="en", start_prompt="🎙️ Start speaking", stop_prompt="⏹️ Stop recording", just_once=True, key=f"main_voice_input_{st.session_state.voice_counter}")
    if _spoken and _spoken.strip():
        st.session_state.voice_counter += 1
        st.session_state.voice_messages.append({"role": "user", "content": _spoken.strip()})
        st.session_state.voice_messages.append({"role": "assistant", "content": process_request(_spoken.strip())})
        st.rerun()
except Exception as _exc:
    st.warning("Microphone input could not start. Allow microphone access in your browser and install streamlit-mic-recorder.")
    with st.expander("Microphone troubleshooting"):
        st.code(str(_exc))

st.caption("Voice input is speech-to-text. This version does not read responses aloud. Impact results are candidates, not guarantees; co-change indicates correlation, not causation.")

st.markdown("""
<div class="footer">
  CHANGEIMPACT AI · GRAPH-BASED CANDIDATES, NOT GUARANTEED FAILURES
  <br/>Python · Streamlit · FalkorDB
</div>
""", unsafe_allow_html=True)
