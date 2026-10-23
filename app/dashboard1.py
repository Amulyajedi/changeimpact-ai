import contextlib
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

st.markdown("""
<div class="footer">
  CHANGEIMPACT AI · GRAPH-BASED CANDIDATES, NOT GUARANTEED FAILURES
  <br/>Python · Streamlit · FalkorDB
</div>
""", unsafe_allow_html=True)
