
import contextlib
import io
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# --------------------------------------------------
# Project paths and backend imports
# --------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"
TARGET_REPO = ROOT / "data" / "target_repo"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from ast_parser import scan_project
from graph_db import get_graph
from impact_analysis import trace_impact


# --------------------------------------------------
# Page setup
# --------------------------------------------------
st.set_page_config(
    page_title="ChangeImpact AI",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0E1117;
        color: #F0F2F6;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    div[data-testid="stMetric"] {
        background: #171B27;
        border: 1px solid #30364A;
        padding: 16px;
        border-radius: 12px;
    }

    .hero {
        padding: 24px;
        border: 1px solid #30364A;
        border-radius: 16px;
        background: linear-gradient(120deg, #171B27, #20243A);
        margin-bottom: 20px;
    }

    .muted {
        color: #AAB2C5;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# Sidebar
# --------------------------------------------------
with st.sidebar:
    st.title("🔍 ChangeImpact AI")
    st.caption("Graph-based code impact analysis")
    st.divider()

    st.markdown("### Workflow")
    st.markdown("1. Select a function")
    st.markdown("2. Analyze its impact")
    st.markdown("3. Review affected functions")
    st.markdown("4. Inspect Git history")

    st.divider()
    st.caption("Python · FalkorDB · Git history")


# --------------------------------------------------
# Header
# --------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <h1>ChangeImpact AI</h1>
        <p class="muted">
            Discover potentially affected code and historical
            file relationships before running your tests.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# Connect to graph database
# --------------------------------------------------
graph = None
connection_error = None

try:
    graph = get_graph()
    # A lightweight query confirms the connection.
    graph.query("RETURN 1")
except Exception as error:
    connection_error = str(error)
    graph = None

if graph is not None:
    st.sidebar.success("FalkorDB connected")
else:
    st.sidebar.error("FalkorDB unavailable")
    st.error(
        "Cannot connect to FalkorDB. Start your existing "
        "FalkorDB container and refresh the dashboard."
    )
    if connection_error:
        with st.expander("Connection details"):
            st.code(connection_error)


# --------------------------------------------------
# Repository overview
# --------------------------------------------------
st.subheader("📁 Repository Overview")

if TARGET_REPO.is_dir():
    try:
        with st.spinner("Scanning Python repository..."):
            modules = scan_project(str(TARGET_REPO))

        module_count = len(modules)
        function_count = sum(
            len(module.get("functions", []))
            for module in modules
        )
        binding_count = sum(
            len(module.get("import_bindings", []))
            for module in modules
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Python modules", module_count)
        c2.metric("Functions & methods", function_count)
        c3.metric("Import bindings", binding_count)

    except Exception as error:
        st.warning(f"Repository scan failed: {error}")
else:
    st.warning(
        f"Repository folder not found: {TARGET_REPO}"
    )


# --------------------------------------------------
# Dependency graph statistics
# --------------------------------------------------
st.divider()
st.subheader("🕸️ Dependency Graph")

if graph is not None:
    try:
        function_result = graph.query(
            "MATCH (f:Function) RETURN count(f)"
        )
        call_result = graph.query(
            "MATCH ()-[r:CALLS]->() RETURN count(r)"
        )
        cochange_result = graph.query(
            "MATCH ()-[r:CO_CHANGED]-() RETURN count(r)"
        )

        function_count_graph = (
            function_result.result_set[0][0]
        )
        call_count = call_result.result_set[0][0]
        cochange_count = cochange_result.result_set[0][0]

        c1, c2, c3 = st.columns(3)
        c1.metric("Function nodes", function_count_graph)
        c2.metric("CALLS relationships", call_count)
        c3.metric(
            "Co-change relationships",
            cochange_count // 2,
        )

        st.caption(
            "The co-change statistic is divided by two because "
            "the undirected match can return each relationship "
            "from both directions."
        )

    except Exception as error:
        st.warning(f"Could not load graph statistics: {error}")


# --------------------------------------------------
# Load functions for selection
# --------------------------------------------------
st.divider()
st.subheader("🎯 Analyze a Code Change")

st.write(
    "Select the function you changed. ChangeImpact AI will "
    "trace connected callers, look for connected test functions, "
    "and retrieve historical co-change information for its file."
)

function_options = []
function_load_error = None

if graph is not None:
    try:
        function_result = graph.query(
            """
            MATCH (f:Function)
            RETURN f.id, f.name, f.module
            ORDER BY f.module, f.name
            """
        )

        for row in function_result.result_set or []:
            function_id, name, module = row

            if function_id:
                function_options.append(
                    {
                        "id": str(function_id),
                        "name": str(name or function_id),
                        "module": str(module or ""),
                    }
                )

        # Avoid duplicate IDs in the selector.
        unique_options = {}
        for item in function_options:
            unique_options[item["id"]] = item
        function_options = list(unique_options.values())

    except Exception as error:
        function_load_error = str(error)

if function_load_error:
    st.error(
        f"Could not load functions from FalkorDB: "
        f"{function_load_error}"
    )

if graph is not None and function_options:
    selected_id = st.selectbox(
        "Choose the changed function",
        options=[item["id"] for item in function_options],
        format_func=lambda function_id: next(
            (
                f"{item['name']}  —  {item['module']}"
                if item["module"]
                else item["name"]
            )
            for item in function_options
            if item["id"] == function_id
        ),
        help="The list is loaded from Function nodes in FalkorDB.",
    )

    max_depth = st.slider(
        "Dependency search depth",
        min_value=1,
        max_value=5,
        value=5,
        help=(
            "How many CALLS relationship hops to search. "
            "Greater depth may find more indirect callers."
        ),
    )

    analyze_clicked = st.button(
        "▶ Analyze Impact",
        type="primary",
        use_container_width=True,
    )

    if analyze_clicked:
        with st.spinner(
            "Tracing dependencies and retrieving Git history..."
        ):
            try:
                # Reuse the existing analysis implementation.
                # Capture its terminal output so it doesn't clutter
                # the Streamlit page.
                captured_output = io.StringIO()

                with contextlib.redirect_stdout(captured_output):
                    impacted, tests, historical_files = trace_impact(
                        selected_id,
                        max_depth=max_depth,
                    )

                # Store structured results for the dashboard.
                st.session_state["impact_results"] = {
                    "selected_id": selected_id,
                    "impacted": impacted,
                    "tests": tests,
                    "historical_files": historical_files,
                }

            except Exception as error:
                st.session_state.pop("impact_results", None)
                st.error(f"Impact analysis failed: {error}")

    # Show the most recent result until another analysis is run.
    results = st.session_state.get("impact_results")

    if results and results["selected_id"] == selected_id:
        impacted = results["impacted"]
        tests = results["tests"]
        historical_files = results["historical_files"]

        st.success("Analysis completed.")

        st.markdown("### Analysis Summary")

        m1, m2, m3 = st.columns(3)
        m1.metric("Affected functions", len(impacted))
        m2.metric("Connected tests", len(tests))
        m3.metric("Historical files", len(historical_files))

        st.markdown("### Changed Function")
        st.code(selected_id, language="text")

        # ------------------------------------------
        # Impacted functions
        # ------------------------------------------
        st.markdown("### 🔗 Potentially Affected Functions")

        if impacted:
            impact_rows = [
                {
                    "Function ID": function_id,
                    "Function": details.get("name", ""),
                    "Dependency distance": details.get("hops", ""),
                }
                for function_id, details in impacted.items()
            ]

            impact_df = pd.DataFrame(impact_rows)
            impact_df = impact_df.sort_values(
                "Dependency distance",
                kind="stable",
            )

            st.dataframe(
                impact_df,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info(
                "No callers were found in the current graph "
                "within the selected search depth."
            )

        # ------------------------------------------
        # Recommended tests
        # ------------------------------------------
        st.markdown("### 🧪 Connected Test Functions")

        if tests:
            test_rows = [
                {
                    "Test function ID": test_id,
                    "Dependency distance": distance,
                }
                for test_id, distance in tests.items()
            ]

            test_df = pd.DataFrame(test_rows)
            test_df = test_df.sort_values(
                "Dependency distance",
                kind="stable",
            )

            st.dataframe(
                test_df,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info(
                "No connected test functions were found by the "
                "current graph query. This does not mean the "
                "code is untested."
            )

        # ------------------------------------------
        # Historical co-changes
        # ------------------------------------------
        st.markdown("### 📜 Historical Co-changes")

        if historical_files:
            history_rows = [
                {
                    "Related file": file_path,
                    "Times changed together": count,
                }
                for file_path, count in historical_files.items()
            ]

            history_df = pd.DataFrame(history_rows)

            history_df["Times changed together"] = pd.to_numeric(
                history_df["Times changed together"],
                errors="coerce",
            )

            history_df = history_df.sort_values(
                "Times changed together",
                ascending=False,
                na_position="last",
            )

            st.dataframe(
                history_df,
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                "Historical frequencies come from the existing "
                "CO_CHANGED relationships in FalkorDB."
            )
        else:
            st.info(
                "No historical co-change records were found for "
                "this function's file. Check whether its module "
                "maps to a File node in the graph."
            )

        st.caption(
            "Impact results represent relationships captured by "
            "the current graph. Dynamic calls and missing graph "
            "edges may not be detected."
        )

elif graph is not None:
    st.warning(
        "No Function nodes were found in FalkorDB. The selector "
        "will populate after the graph contains function nodes."
    )


# --------------------------------------------------
# Footer
# --------------------------------------------------
st.divider()
st.caption("ChangeImpact AI | Graph Hacks — Track 01")
