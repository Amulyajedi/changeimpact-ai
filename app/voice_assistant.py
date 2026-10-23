"""ChangeImpact Voice: standalone MCP-powered voice assistant."""
import asyncio
import json
import re
from typing import Any

import streamlit as st
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from streamlit_mic_recorder import speech_to_text

MCP_URL = "http://127.0.0.1:8000/mcp"

st.set_page_config(page_title="ChangeImpact Voice", page_icon="🎙️", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.stApp{background:#0b1120;color:#e5e7eb}.block-container{padding-top:1.5rem}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0a1020,#101b2d 60%,#0c1423);border-right:1px solid #24354b}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{color:#f1f5f9}
.sidebar-brand{padding:18px 14px;border:1px solid #263e55;border-radius:16px;background:linear-gradient(135deg,#13253a,#102f40);margin-bottom:18px}
.sidebar-name{font-size:18px;font-weight:800;letter-spacing:1.2px;color:#f8fafc}.sidebar-tagline{color:#67e8f9;font-size:9px;letter-spacing:1.4px;margin-top:5px}
.sidebar-section{color:#7f93ad;font-size:10px;font-weight:700;letter-spacing:1.8px;margin:20px 0 9px 4px}
.sidebar-note{padding:13px;border-radius:12px;background:#111e30;border:1px solid #24354b;color:#cbd5e1;font-size:12px;line-height:1.65}
[data-testid="stSidebar"] [data-testid="stButton"] button{border:1px solid #2b4058;border-radius:10px;background:#142237;color:#e2e8f0}
.hero{padding:25px;border:1px solid #263449;border-radius:18px;background:linear-gradient(120deg,#111c32,#132b40);margin-bottom:20px}
.hero h1{color:#67e8f9;margin-bottom:8px}.hero p{color:#cbd5e1;font-size:16px}.status-line{color:#67e8f9;font-size:12px;letter-spacing:.3px}
div[data-testid="stChatMessage"]{border:1px solid #263449;border-radius:12px;padding:12px}
div[data-testid="stMetric"]{background:#111e30;border:1px solid #263449;padding:12px;border-radius:12px}
.code-chip{background:#13243a;border:1px solid #2b4058;border-radius:7px;padding:3px 7px;font-family:monospace;overflow-wrap:anywhere}
</style>
""", unsafe_allow_html=True)

for key, default in (("messages", []), ("voice_counter", 0), ("sidebar_prompt", "")):
    if key not in st.session_state:
        st.session_state[key] = default


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
        cleaned = re.sub(r"[.:/\\]+", " ", cleaned)
        cleaned = re.sub(r"\b(src|requests?|models?|module|file|function|the|a|an|of|for|please|code|change|impact|analyse|analyze|on|to|me|what|is|are|should|could|might|happen|if|test|tests|recommendations?)\b", " ", cleaned, flags=re.I)
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9_]*", cleaned)
        if tokens:
            term = "_".join(tokens[-3:]).strip("_")
            return "impact_search", {"search_term": term, "limit": 10}, f"I'll find `{term}` and analyze its potential impact."
        return "help", None, "Please provide a function name or complete ID, e.g. `src.requests.models:_encode_files`."

    if any(p in lower for p in ("search", "find", "look for", "where is", "show functions", "function named")):
        term = message
        term = re.sub(r"^(please\s+)?(search|find|look for|show)\s+", "", term, flags=re.I)
        term = re.sub(r"^(the\s+)?functions?\s*[:=-]?\s*", "", term, flags=re.I)
        term = term.strip().strip(" :.,!?;\"'`")
        term = re.sub(r"^[^A-Za-z0-9_]+|[^A-Za-z0-9_]+$", "", term).strip()
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


with st.sidebar:
    st.markdown('<div class="sidebar-brand"><div style="font-size:28px">⌘ ◈</div><div class="sidebar-name">CHANGEIMPACT</div><div class="sidebar-tagline">CODE INTELLIGENCE PLATFORM</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section">WORKSPACE</div>', unsafe_allow_html=True)
    st.markdown("**🎙️ ChangeImpact Voice**")
    st.caption("Conversational code intelligence")
    st.markdown('<div class="sidebar-section">CONNECTED SERVICES</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-note"><b>◉ FalkorDB</b><br>Graph database · check on demand<br><br><b>◉ MCP Server</b><br>Streamable HTTP · localhost:8000</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section">QUICK COMMANDS</div>', unsafe_allow_html=True)
    if st.button("⌕ Search a function", use_container_width=True):
        st.session_state.sidebar_prompt = "Find the function prepare_body"
    if st.button("⌁ Analyze code impact", use_container_width=True):
        st.session_state.sidebar_prompt = "Analyze the impact of src.requests.models:_encode_files"
    if st.button("◷ Historical co-changes", use_container_width=True):
        st.session_state.sidebar_prompt = "Find files historically changed with src/requests/models.py"
    if st.button("✦ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.sidebar_prompt = ""
        st.rerun()
    st.markdown("---")
    st.markdown('<div class="sidebar-note"><b style="color:#67e8f9">KNOW THE RIPPLE.</b><br>Trace dependencies. Discover risk. Recommend targeted tests.</div>', unsafe_allow_html=True)
    st.caption("CHANGEIMPACT AI · DEVELOPER EDITION")

st.markdown('<div class="hero"><h1>🎙️ ChangeImpact Voice</h1><p>Your conversational assistant for code changes, dependency analysis, and test recommendations.</p><div class="status-line">MCP STREAMABLE HTTP · FALKORDB · CODE IMPACT INTELLIGENCE</div></div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
c1.metric("Input modes", "Text + Voice")
c2.metric("MCP tools", "3")
c3.metric("Workspace", "Code graph")
st.caption("Voice recognition requires microphone permission in your browser. Results depend on the current graph and available MCP tools.")

for item in st.session_state.messages:
    with st.chat_message(item["role"]):
        content = item["content"]
        if item["role"] == "user":
            st.markdown(content)
        else:
            st.markdown(content.get("message", "No response message."))
            tool = content.get("tool")
            if tool:
                st.caption(f"MCP tool executed: {tool}")
            result = content.get("result")
            if result is not None:
                if tool == "analyze_change_impact":
                    render_impact_result(result)
                else:
                    st.json(result)

if st.session_state.sidebar_prompt:
    prompt = st.session_state.sidebar_prompt
    st.session_state.sidebar_prompt = ""
    submit_request(prompt)
    st.rerun()

st.divider()
st.subheader("Ask your codebase")
with st.form("chat_form", clear_on_submit=True):
    typed_text = st.text_input("Your request", placeholder="Analyze the impact of src.requests.models:_encode_files")
    submitted = st.form_submit_button("➤ Send request", type="primary", use_container_width=True)
if submitted and typed_text.strip():
    submit_request(typed_text)
    st.rerun()

st.markdown("### Or speak to ChangeImpact Voice")
try:
    voice_text = speech_to_text(language="en", start_prompt="🎙️ Start speaking", stop_prompt="⏹️ Stop recording", just_once=True, key=f"voice_input_{st.session_state.voice_counter}")
    if voice_text and voice_text.strip():
        st.session_state.voice_counter += 1
        submit_request(voice_text)
        st.rerun()
except Exception as exc:
    st.warning("Microphone input could not start. Check browser microphone permission and confirm streamlit-mic-recorder is installed.")
    with st.expander("Microphone details"):
        st.code(str(exc))

st.caption("Impact results are candidates, not guarantees. Historical co-changes show correlation, not causation.")
