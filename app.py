"""
NL-to-SQL -- Streamlit application entry point.

Run with:
    streamlit run app.py

This module wires together the UI layer (Streamlit widgets) and the
backend agent (``nltosql.agent.run_agent``).  It is intentionally kept
thin -- all business logic lives in the ``nltosql`` package.
"""

import os
import time

import pandas as pd
import streamlit as st

# =============================================================================
# Page configuration (must be the first Streamlit call)
# =============================================================================

st.set_page_config(
    page_title="NL to SQL",
    page_icon=":mag:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -- Custom CSS for a clean, minimalist look ----------------------------------

st.markdown(
    """
    <style>
        .block-container { padding-top: 2rem; }
        #MainMenu { visibility: hidden; }
        footer    { visibility: hidden; }
        [data-testid="stSidebar"] { background-color: #fafafa; }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# Sidebar -- database schema browser and settings
# =============================================================================

with st.sidebar:
    st.markdown("### Database Schema")

    db_path = st.text_input(
        "Database path",
        value=os.getenv("DB_PATH", "data/sample.db"),
        help="Path to your SQLite database file.",
    )

    # Allow uploading a custom database file.
    uploaded_file = st.file_uploader(
        "Or upload a .db file",
        type=["db", "sqlite", "sqlite3"],
        help="Upload your own SQLite database.",
    )
    if uploaded_file is not None:
        upload_dir = "data"
        os.makedirs(upload_dir, exist_ok=True)
        upload_path = os.path.join(upload_dir, uploaded_file.name)
        with open(upload_path, "wb") as fh:
            fh.write(uploaded_file.getvalue())
        db_path = upload_path
        st.success(f"Uploaded: {uploaded_file.name}")

    # Display schema tree when the database exists.
    if os.path.exists(db_path):
        from nltosql.db_manager import get_tables

        tables = get_tables(db_path)
        if tables:
            st.markdown("---")
            for table in tables:
                with st.expander(f"**{table['name']}** ({table['row_count']} rows)"):
                    for col in table["columns"]:
                        pk_label = " [PK]" if col["pk"] else ""
                        st.text(f"  {col['name']}  ({col['type']}){pk_label}")
        else:
            st.warning("No tables found in the database.")
    else:
        st.error(f"Database not found: `{db_path}`")
        st.info("Run `python scripts/create_sample_db.py` to create the sample database.")

    st.markdown("---")

    # Display current configuration.
    with st.expander("Settings"):
        from nltosql.config import MAX_RETRIES, OLLAMA_BASE_URL, OLLAMA_MODEL

        st.text(f"Model:       {OLLAMA_MODEL}")
        st.text(f"Ollama URL:  {OLLAMA_BASE_URL}")
        st.text(f"Max retries: {MAX_RETRIES}")

# =============================================================================
# Main area -- query input and results
# =============================================================================

st.markdown("# NL to SQL")
st.markdown(
    "Ask questions about your data in plain English. "
    "The agent will generate SQL, execute it, and show you the results."
)

question = st.text_area(
    "Your question",
    placeholder="e.g. Show me the top 5 customers by total order value...",
    height=80,
    label_visibility="collapsed",
)

col_run, _ = st.columns([1, 8])
with col_run:
    run_clicked = st.button("Run", type="primary", use_container_width=True)

# =============================================================================
# Query execution
# =============================================================================

if run_clicked and question:
    if not os.path.exists(db_path):
        st.error("Database not found. Please check the path or upload a database.")
    else:
        from nltosql.agent import run_agent

        with st.status("Agent is working...", expanded=True) as status:
            st.write("Starting trial-and-error agent...")
            wall_start = time.time()

            result = run_agent(question, db_path=db_path)

            wall_elapsed = round(time.time() - wall_start, 1)
            attempts = result["attempts"]
            suffix = "s" if attempts != 1 else ""

            if result["success"]:
                status.update(
                    label=f"Done in {wall_elapsed}s ({attempts} attempt{suffix})",
                    state="complete",
                )
            else:
                status.update(
                    label=f"Failed after {attempts} attempt{suffix}",
                    state="error",
                )

        st.markdown("---")

        # -- Agent activity log -----------------------------------------------
        with st.expander(
            f"Agent Activity Log ({attempts} attempt{suffix})",
            expanded=not result["success"],
        ):
            for step in result.get("agent_log", []):
                step_status = step.get("status", "")
                msg = step.get("message", "")

                if step_status == "success":
                    st.success(f"[OK] {msg}")
                elif step_status == "error":
                    st.error(f"[ERROR] {msg}")
                else:
                    st.info(f"[...] {msg}")

                if step.get("sql"):
                    st.code(step["sql"], language="sql")

        # -- Success path -----------------------------------------------------
        if result["success"]:
            st.markdown("### SQL")
            st.code(result["sql"], language="sql")

            if result["data"]:
                st.markdown(f"### Results ({len(result['data'])} rows)")
                st.dataframe(
                    pd.DataFrame(result["data"]),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Query returned no results.")

            if result.get("explanation"):
                st.markdown("### Summary")
                st.info(result["explanation"])

            if attempts > 1:
                st.warning(
                    f"The agent needed **{attempts} attempts** to produce a "
                    "working query. Expand the Agent Activity Log above to "
                    "see the trial-and-error process."
                )

        # -- Failure path -----------------------------------------------------
        else:
            st.error(result.get("error", "Unknown error"))
            st.info(
                "Try rephrasing your question, or verify that the database "
                "contains the tables you are asking about."
            )

# =============================================================================
# Example queries (shown when the input is empty)
# =============================================================================

if not question:
    st.markdown("---")
    st.markdown("### Example queries")

    _EXAMPLES = [
        "Show me all customers from New York",
        "What are the top 5 most expensive products?",
        "How many orders were placed each month?",
        "Which customers have spent the most money?",
        "What is the average rating for each product category?",
        "List products that have never been ordered",
    ]

    cols = st.columns(2)
    for idx, example in enumerate(_EXAMPLES):
        with cols[idx % 2]:
            st.markdown(f"- _{example}_")
