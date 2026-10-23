
import asyncio
import json
from datetime import datetime

import streamlit as st
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


# ============================================================
# Configuration
# ============================================================

MCP_URL = "http://127.0.0.1:8000/mcp"

st.set_page_config(
    page_title="ChangeImpact | Developer Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# Premium dark dashboard styling
# ============================================================

st.markdown(
    """
    <style>
    :root {
        --bg: #080d17;
        --panel: #101a2b;
        --panel2: #0c1422;
        --border: #26364c;
        --text: #edf4ff;
        --muted: #91a2ba;
        --cyan: #5eead4;
        --blue: #60a5fa;
    }

    .stApp {
        background:
            radial-gradient(ellipse at 78% 0%, #152746 0%, transparent 33%),
            var(--bg);
        color: var(--text);
    }

    [data-testid="stSidebar"] {
        background: #0a1220;
        border-right: 1px solid var(--border);
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.6rem;
    }

    .block-container {
        max-width: 1450px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        color: var(--text);
        letter-spacing: -0.5px;
    }

    p, label, .stMarkdown {
        color: var(--text);
    }

    .eyebrow {
        color: var(--cyan);
        font-size: 0.74rem;
        font-weight: 800;
        letter-spacing: 2.2px;
        text-transform: uppercase;
        margin-bottom: 12px;
    }

    .hero-title {
        font-size: clamp(2.5rem, 5vw, 4rem);
        line-height: 1.03;
        font-weight: 850;
        letter-spacing: -2.5px;
        margin: 0;
        color: #f5f8ff;
    }

    .hero-title span {
        color: var(--cyan);
    }

    .hero-description {
        max-width: 760px;
        color: var(--muted);
        font-size: 1.04rem;
        line-height: 1.8;
        margin-top: 16px;
        margin-bottom: 26px;
    }

    .section-label {
        color: var(--muted);
        font-size: 0.76rem;
        font-weight: 800;
        letter-spacing: 1.6px;
        text-transform: uppercase;
        margin: 12px 0;
    }

    .surface {
        background: linear-gradient(145deg, #121e31, #0d1625);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 12px;
    }

    .metric-card {
        background: linear-gradient(145deg, #142238, #0d1625);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 18px 20px;
        min-height: 125px;
    }

    .metric-label {
        color: var(--muted);
        font-size: 0.74rem;
        font-weight: 800;
        letter-spacing: 1.2px;
        text-transform: uppercase;
    }

    .metric-value {
        color: #f2f7ff;
        font-size: 1.65rem;
        font-weight: 850;
        margin-top: 12px;
        letter-spacing: -0.7px;
    }

    .metric-note {
        color: var(--muted);
        font-size: 0.8rem;
        margin-top: 4px;
    }

    .tool-title {
        color: #f2f7ff;
        font-weight: 800;
        font-size: 1.05rem;
        margin-bottom: 8px;
    }

    .tool-description {
        color: var(--muted);
        line-height: 1.65;
        font-size: 0.92rem;
    }

    .tool-number {
        color: var(--cyan);
        font-size: 0.75rem;
        letter-spacing: 1.5px;
        font-weight: 800;
        margin-bottom: 12px;
    }

    .status-pill {
        display: inline-block;
        color: var(--cyan);
        background: #102d30;
        border: 1px solid #235653;
        border-radius: 999px;
        padding: 5px 10px;
        font-size: 0.75rem;
        font-weight: 800;
    }

    .muted {
        color: var(--muted);
    }

    .stButton > button,
    [data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(105deg, #0f766e, #1d4ed8);
        color: white;
        border: 1px solid #367b9a;
        border-radius: 10px;
        min-height: 44px;
        font-weight: 750;
        transition: 150ms ease;
    }

    .stButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        border-color: var(--cyan);
        color: white;
        filter: brightness(1.1);
    }

    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    div[data-baseweb="textarea"] > div {
        background: #0b1422;
        border-color: #2b3b51;
        border-radius: 9px;
    }

    input, textarea {
        color: #edf4ff !important;
    }

    [data-testid="stMetric"] {
        background: #101a2b;
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 15px;
    }

    [data-testid="stMetricLabel"] {
        color: var(--muted);
    }

    [data-testid="stMetricValue"] {
        color: #f2f7ff;
    }

    div[data-testid="stExpander"] {
        background: #0d1625;
        border: 1px solid var(--border);
        border-radius: 12px;
    }

    hr {
        border-color: var(--border);
    }

    code {
        color: #a5f3fc;
    }

    footer {
        visibility: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# MCP client
# ============================================================

async def call_mcp_tool(tool_name, arguments):
    async with streamablehttp_client(MCP_URL) as (
        read_stream,
        write_stream,
        _get_session_id,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            return await session.call_tool(tool_name, arguments)


async def check_mcp_connection():
    async with streamablehttp_client(MCP_URL) as (
        read_stream,
        write_stream,
        _get_session_id,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            response = await session.list_tools()
            return [tool.name for tool in response.tools]


def parse_mcp_result(result):
    output = []

    for item in getattr(result, "content", []) or []:
        value = getattr(item, "text", None)

        if value:
            try:
                output.append(json.loads(value))
            except json.JSONDecodeError:
                output.append(value)

    if len(output) == 1:
        return output[0]

    return output


def run_tool(tool_name, arguments):
    try:
        with st.spinner(f"Running {tool_name.replace('_', ' ')}..."):
            result = asyncio.run(call_mcp_tool(tool_name, arguments))

        response = parse_mcp_result(result)
        is_error = bool(getattr(result, "isError", False))

        entry = {
            "tool": tool_name,
            "arguments": arguments,
            "result": response,
            "is_error": is_error,
            "called_at": datetime.now().astimezone().strftime(
                "%d %b %Y · %H:%M:%S"
            ),
        }

        st.session_state.last_call = entry
        st.session_state.history.insert(0, entry)
        st.session_state.history = st.session_state.history[:10]

        if is_error:
            st.error("The MCP tool returned an error.")
        else:
            st.success("Analysis completed.")

    except Exception as exc:
        entry = {
            "tool": tool_name,
            "arguments": arguments,
            "result": {
                "error": str(exc),
                "hint": (
                    "Check that FalkorDB is running and the MCP server "
                    "is available at the configured endpoint."
                ),
            },
            "is_error": True,
            "called_at": datetime.now().astimezone().strftime(
                "%d %b %Y · %H:%M:%S"
            ),
        }

        st.session_state.last_call = entry
        st.session_state.history.insert(0, entry)
        st.session_state.history = st.session_state.history[:10]

        st.error("Could not complete the MCP request.")
        st.caption(
            "Confirm that FalkorDB and `python -m app.mcp_server` "
            "are running in separate terminals."
        )


# ============================================================
# Session state
# ============================================================

if "last_call" not in st.session_state:
    st.session_state.last_call = None

if "history" not in st.session_state:
    st.session_state.history = []

if "available_tools" not in st.session_state:
    st.session_state.available_tools = None


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:
    st.markdown(
        """
        <div style="font-size:1.7rem;font-weight:900;letter-spacing:-1px">
            <span style="color:#5eead4">◈</span> ChangeImpact
        </div>
        <div style="color:#91a2ba;font-size:0.72rem;
                    font-weight:800;letter-spacing:1.7px;margin-top:4px">
            DEVELOPER INTELLIGENCE
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown('<div class="section-label">Workspace</div>',
                unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        [
            "Overview",
            "Search Functions",
            "Analyze Impact",
            "Historical Co-changes",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown('<div class="section-label">Connection</div>',
                unsafe_allow_html=True)

    st.caption("MCP · Streamable HTTP")
    st.code(MCP_URL, language="text")

    if st.button("Check connection", use_container_width=True):
        try:
            with st.spinner("Checking MCP server..."):
                tools = asyncio.run(check_mcp_connection())

            st.session_state.available_tools = tools
            st.success(f"Connected · {len(tools)} tools discovered")

        except Exception as exc:
            st.session_state.available_tools = None
            st.error("MCP server unreachable")
            st.caption(str(exc))

    if st.session_state.available_tools is not None:
        with st.expander("Discovered MCP tools"):
            for tool in st.session_state.available_tools:
                st.write(f"• `{tool}`")

    st.divider()

    st.markdown(
        """
        <div style="color:#91a2ba;font-size:0.8rem;line-height:1.8">
            <b style="color:#dbeafe">Powered by</b><br>
            Python · MCP · FalkorDB<br><br>
            Graph-based code analysis<br>
            Built for targeted testing
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# Header
# ============================================================

st.markdown(
    '<div class="eyebrow">CODEBASE ANALYSIS / MCP WORKSPACE</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-title">
        See the ripple.<br>
        <span>Test with intent.</span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-description">
        Understand where code changes may travel, discover potentially
        affected functions, and use historical co-changes to help prioritize
        your testing strategy.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Overview metrics
# ============================================================

m1, m2, m3 = st.columns(3)

with m1:
    st.markdown(
        """
        <div class="metric-card">
            <div class="metric-label">Analysis tools</div>
            <div class="metric-value">03</div>
            <div class="metric-note">Search · Impact · History</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with m2:
    st.markdown(
        """
        <div class="metric-card">
            <div class="metric-label">Graph backend</div>
            <div class="metric-value">FalkorDB</div>
            <div class="metric-note">Dependency relationship analysis</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with m3:
    last_tool = (
        st.session_state.last_call["tool"].replace("_", " ").title()
        if st.session_state.last_call
        else "No activity yet"
    )

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Latest operation</div>
            <div class="metric-value" style="font-size:1.25rem">
                {last_tool}
            </div>
            <div class="metric-note">Updates after each tool call</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# Main workspace
# ============================================================

if page == "Overview":
    st.markdown("## Analysis workspace")
    st.markdown(
        '<div class="muted">Choose a workflow to start exploring your codebase.</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)

    with left:
        st.markdown(
            """
            <div class="surface">
                <div class="tool-number">01 / DISCOVER</div>
                <div class="tool-title">Search Functions</div>
                <div class="tool-description">
                    Locate functions by name or identifier before investigating
                    a potential code change.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Open function search →", key="open_search",
                     use_container_width=True):
            st.session_state.workspace_page = "Search Functions"
            st.rerun()

        st.markdown(
            """
            <div class="surface">
                <div class="tool-number">02 / TRACE</div>
                <div class="tool-title">Analyze Change Impact</div>
                <div class="tool-description">
                    Trace graph relationships from a changed function and
                    identify candidates for further testing.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Open impact analysis →", key="open_impact",
                     use_container_width=True):
            st.session_state.workspace_page = "Analyze Impact"
            st.rerun()

    with right:
        st.markdown(
            """
            <div class="surface">
                <div class="tool-number">03 / INVESTIGATE</div>
                <div class="tool-title">Historical Co-changes</div>
                <div class="tool-description">
                    Inspect files that have changed together historically.
                    Use these patterns as additional testing context.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Open co-change analysis →", key="open_history",
                     use_container_width=True):
            st.session_state.workspace_page = "Historical Co-changes"
            st.rerun()

        st.markdown(
            """
            <div class="surface">
                <div class="tool-number">WORKFLOW / RECOMMENDED</div>
                <div class="tool-title">From change to test plan</div>
                <div class="tool-description">
                    Find the function → trace potential impact → review
                    relevant history → inspect the returned evidence.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.session_state.history:
        st.markdown("## Recent activity")

        for entry in st.session_state.history[:5]:
            icon = "⚠" if entry["is_error"] else "↗"

            with st.expander(
                f"{icon}  {entry['tool'].replace('_', ' ').title()}  ·  "
                f"{entry['called_at']}"
            ):
                st.json({
                    "arguments": entry["arguments"],
                    "error": entry["is_error"],
                    "result": entry["result"],
                })

    if st.session_state.last_call is None:
        st.info(
            "No analysis has been run in this session yet. "
            "Choose a workflow above to begin."
        )


elif page == "Search Functions":
    st.markdown("## Search Functions")
    st.caption(
        "Search your indexed codebase for matching function names or identifiers."
    )

    with st.form("search_form"):
        term = st.text_input(
            "Function or module name",
            value="_encode_files",
            placeholder="e.g. prepare_body",
        )

        limit = st.slider("Maximum results", 1, 50, 10)

        submit = st.form_submit_button(
            "⌕  Search functions",
            use_container_width=True,
        )

    if submit:
        if not term.strip():
            st.warning("Enter a function or module name first.")
        else:
            run_tool(
                "search_functions",
                {"search_term": term.strip(), "limit": limit},
            )


elif page == "Analyze Impact":
    st.markdown("## Analyze Change Impact")
    st.caption(
        "Trace functions that may be affected by a change to the selected function."
    )

    with st.form("impact_form"):
        function_id = st.text_input(
            "Changed function ID",
            value="src.requests.models:_encode_files",
            help="Use the function ID returned by Search Functions.",
        )

        depth = st.slider(
            "Maximum dependency depth",
            min_value=1,
            max_value=10,
            value=5,
            help="Higher depth may reveal longer dependency paths.",
        )

        submit = st.form_submit_button(
            "◎  Trace change impact",
            use_container_width=True,
        )

    if submit:
        if not function_id.strip():
            st.warning("Enter a function ID first.")
        else:
            run_tool(
                "analyze_change_impact",
                {
                    "changed_function_id": function_id.strip(),
                    "max_depth": depth,
                },
            )


elif page == "Historical Co-changes":
    st.markdown("## Historical Co-changes")
    st.caption(
        "Explore files that have been changed together in repository history."
    )

    with st.form("cochange_form"):
        path = st.text_input(
            "Repository-relative file path",
            value="src/requests/models.py",
            help="Enter a path relative to the indexed repository.",
        )

        limit = st.slider("Maximum related files", 1, 50, 10)

        submit = st.form_submit_button(
            "↗  Find co-changes",
            use_container_width=True,
        )

    if submit:
        if not path.strip():
            st.warning("Enter a repository-relative file path first.")
        else:
            run_tool(
                "get_historical_cochanges",
                {"file_path": path.strip(), "limit": limit},
            )


# ============================================================
# Response console
# ============================================================

st.divider()

st.markdown("## Response Console")
st.caption(
    "Inspect the actual response returned by the MCP server."
)

last_call = st.session_state.last_call

if last_call is None:
    st.markdown(
        """
        <div class="surface">
            <div class="tool-title">Awaiting first tool call</div>
            <div class="tool-description">
                Run a search, impact analysis, or historical co-change query.
                The raw result will be available here.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    status_label = "Error" if last_call["is_error"] else "Completed"

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Last tool", last_call["tool"].replace("_", " ").title())

    with c2:
        st.metric("Status", status_label)

    with c3:
        st.metric("Session calls", len(st.session_state.history))

    st.caption(f"Executed: {last_call['called_at']}")

    result_tab, args_tab, history_tab = st.tabs(
        ["Result", "Arguments", "Recent calls"]
    )

    with result_tab:
        st.json(last_call["result"], expanded=True)

        st.download_button(
            "Download result as JSON",
            data=json.dumps(
                last_call["result"],
                indent=2,
                ensure_ascii=False,
            ),
            file_name="changeimpact_result.json",
            mime="application/json",
            use_container_width=True,
        )

    with args_tab:
        st.json(last_call["arguments"], expanded=True)

    with history_tab:
        if not st.session_state.history:
            st.caption("No recorded calls.")
        else:
            for index, entry in enumerate(st.session_state.history, start=1):
                with st.expander(
                    f"{index}. {entry['tool'].replace('_', ' ').title()} · "
                    f"{entry['called_at']}"
                ):
                    st.write("Arguments")
                    st.json(entry["arguments"])

                    st.write("Result")
                    st.json(entry["result"])


# ============================================================
# Footer
# ============================================================

st.divider()

st.markdown(
    """
    <div style="text-align:center;color:#71839c;font-size:0.8rem;
                line-height:1.8;padding:8px 0">
        CHANGEIMPACT · DEVELOPER INTELLIGENCE<br>
        Graph paths and historical co-changes are decision-support signals,
        not proof that a change will cause a failure.
    </div>
    """,
    unsafe_allow_html=True,
)
