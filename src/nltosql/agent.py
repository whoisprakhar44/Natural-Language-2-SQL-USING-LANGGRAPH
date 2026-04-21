"""
LangGraph trial-and-error SQL agent.

Defines the agent as a directed graph with five nodes and conditional
edges.  The key design element is the **cycle** from ``handle_error``
back to ``generate_sql``, which implements the self-correction loop:

    START --> generate_sql --> validate_sql --> execute_sql --> explain_result --> END
                  ^                |                |
                  |           handle_error <--------+
                  |                |
                  +--- (retries) --+--- (exhausted) --> END

Each node reads from and writes to a shared ``AgentState`` dictionary.
The conditional-edge functions inspect the state to decide which node
to visit next, forming the trial-and-error loop.
"""

import time
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from nltosql.config import MAX_RETRIES, OLLAMA_BASE_URL, OLLAMA_MODEL, TEMPERATURE
from nltosql.db_manager import execute_query
from nltosql.prompts import (
    CORRECTION_PROMPT,
    EXPLANATION_PROMPT,
    GENERATION_PROMPT,
    SYSTEM_PROMPT,
)
from nltosql.schema_extractor import get_schema_ddl
from nltosql.sql_validator import clean_llm_sql, validate_sql

# -- LLM client (initialised once, reused across invocations) -----------------

_llm = ChatOllama(
    model=OLLAMA_MODEL,
    temperature=TEMPERATURE,
    base_url=OLLAMA_BASE_URL,
)


# =============================================================================
# State
# =============================================================================


class AgentState(TypedDict):
    """Shared state dictionary passed between all graph nodes.

    Every field is readable and writable by any node.  LangGraph
    automatically merges the partial dicts returned by each node
    into this state object.
    """

    question: str                     # User's natural-language question
    schema_ddl: str                   # CREATE TABLE statements for the target DB
    generated_sql: str                # Most recent SQL attempt
    sql_valid: bool                   # Whether the last validation passed
    execution_success: bool           # Whether the last execution succeeded
    results: list[dict[str, Any]]     # Rows returned by a successful execution
    error_message: str                # Last error (validation or execution)
    attempt: int                      # Number of attempts made so far
    max_attempts: int                 # Upper bound on retries
    agent_log: list[dict[str, Any]]   # Step-by-step trace for the UI
    explanation: str                  # Plain-English summary of the results
    db_path: str                      # Path to the active database file


# =============================================================================
# Graph nodes
# =============================================================================


def generate_sql_node(state: AgentState) -> dict[str, Any]:
    """Generate SQL from the user question, or regenerate with error context.

    On the first attempt the prompt contains only the schema and question.
    On subsequent attempts the previous failing SQL and its error message
    are included so that the LLM can diagnose and correct the issue.
    """
    start_time = time.time()
    log = list(state.get("agent_log", []))
    attempt = state.get("attempt", 0)

    if attempt == 0:
        prompt = GENERATION_PROMPT.format(
            schema=state["schema_ddl"],
            question=state["question"],
        )
        log.append(_log_entry("generate", "working",
                              f"Generating SQL (attempt {attempt + 1})..."))
    else:
        # Retry: include previous SQL and error for self-correction.
        prompt = CORRECTION_PROMPT.format(
            schema=state["schema_ddl"],
            question=state["question"],
            previous_sql=state.get("generated_sql", ""),
            error=state.get("error_message", "Unknown error"),
        )
        log.append(_log_entry("fix", "working",
                              f"Fixing SQL (attempt {attempt + 1}/{state['max_attempts']})..."))

    response = _llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])

    sql = clean_llm_sql(response.content)
    elapsed = round(time.time() - start_time, 1)
    log.append(_log_entry("generated", "success",
                          f"SQL generated in {elapsed}s", sql=sql))

    return {"generated_sql": sql, "attempt": attempt + 1, "agent_log": log}


def validate_sql_node(state: AgentState) -> dict[str, Any]:
    """Run safety and syntax checks on the generated SQL.

    A failing validation produces the same downstream effect as a
    failing execution: the error message is stored in state so that
    ``handle_error_node`` can feed it back into the correction prompt.
    """
    log = list(state.get("agent_log", []))
    result = validate_sql(state["generated_sql"], state.get("db_path"))

    if result.is_valid:
        log.append(_log_entry("validate", "success",
                              "SQL passed safety and syntax validation"))
    else:
        log.append(_log_entry("validate", "error",
                              f"Validation failed: {result.error}"))

    return {
        "sql_valid": result.is_valid,
        "error_message": result.error if not result.is_valid else state.get("error_message", ""),
        "agent_log": log,
    }


def execute_sql_node(state: AgentState) -> dict[str, Any]:
    """Execute the validated SQL against the target database.

    Runtime errors (e.g. ``no such column``) are caught and stored in
    state so that the retry loop can pass them to the LLM.
    """
    log = list(state.get("agent_log", []))
    start_time = time.time()

    try:
        rows = execute_query(state["generated_sql"], state.get("db_path"))
        elapsed = round(time.time() - start_time, 2)
        log.append(_log_entry("execute", "success",
                              f"Query executed -- {len(rows)} rows returned in {elapsed}s"))
        return {"results": rows, "execution_success": True, "agent_log": log}

    except Exception as exc:
        elapsed = round(time.time() - start_time, 2)
        error_msg = str(exc)
        log.append(_log_entry("execute", "error",
                              f"Execution error ({elapsed}s): {error_msg}"))
        return {
            "results": [],
            "execution_success": False,
            "error_message": error_msg,
            "agent_log": log,
        }


def explain_result_node(state: AgentState) -> dict[str, Any]:
    """Produce a natural-language summary of the query results."""
    log = list(state.get("agent_log", []))

    # Limit the preview sent to the LLM to avoid exceeding context.
    preview = state["results"][:20]
    results_text = str(preview)
    if len(state["results"]) > 20:
        results_text += f"\n... and {len(state['results']) - 20} more rows"

    prompt = EXPLANATION_PROMPT.format(
        question=state["question"],
        sql=state["generated_sql"],
        results=results_text,
    )
    response = _llm.invoke([
        SystemMessage(content="You are a helpful data analyst. Provide clear, concise summaries."),
        HumanMessage(content=prompt),
    ])

    log.append(_log_entry("explain", "success",
                          "Generated plain-English explanation"))
    return {"explanation": response.content, "agent_log": log}


def handle_error_node(state: AgentState) -> dict[str, Any]:
    """Record the error and prepare state for a potential retry.

    This node is intentionally lightweight -- its primary role is to
    act as a routing waypoint.  The conditional edge originating here
    decides whether to loop back to ``generate_sql`` or terminate.
    """
    log = list(state.get("agent_log", []))
    log.append(_log_entry("retry_decision", "working",
                          f"Error on attempt {state['attempt']}/{state['max_attempts']}"))
    return {"agent_log": log}


# =============================================================================
# Routing functions (conditional edges)
# =============================================================================


def _route_after_validation(state: AgentState) -> str:
    """Decide the next node after SQL validation."""
    return "execute_sql" if state.get("sql_valid") else "handle_error"


def _route_after_execution(state: AgentState) -> str:
    """Decide the next node after SQL execution."""
    return "explain_result" if state.get("execution_success") else "handle_error"


def _route_retry_or_end(state: AgentState) -> str:
    """Decide whether to retry or give up.

    If attempts remain, the graph loops back to ``generate_sql`` --
    this is the cycle that implements trial-and-error.
    """
    if state.get("attempt", 0) < state.get("max_attempts", MAX_RETRIES):
        return "generate_sql"
    return "end"


# =============================================================================
# Graph assembly
# =============================================================================


def _build_agent() -> Any:
    """Construct and compile the LangGraph agent.

    The compiled graph is a callable that accepts an ``AgentState`` dict
    and returns the final state after all nodes have executed (including
    any retry cycles).
    """
    graph = StateGraph(AgentState)

    # -- Nodes --
    graph.add_node("generate_sql", generate_sql_node)
    graph.add_node("validate_sql", validate_sql_node)
    graph.add_node("execute_sql", execute_sql_node)
    graph.add_node("explain_result", explain_result_node)
    graph.add_node("handle_error", handle_error_node)

    # -- Edges --
    graph.add_edge(START, "generate_sql")
    graph.add_edge("generate_sql", "validate_sql")

    graph.add_conditional_edges(
        "validate_sql",
        _route_after_validation,
        {"execute_sql": "execute_sql", "handle_error": "handle_error"},
    )
    graph.add_conditional_edges(
        "execute_sql",
        _route_after_execution,
        {"explain_result": "explain_result", "handle_error": "handle_error"},
    )

    graph.add_edge("explain_result", END)

    # The retry cycle: handle_error --> generate_sql (if retries remain).
    graph.add_conditional_edges(
        "handle_error",
        _route_retry_or_end,
        {"generate_sql": "generate_sql", "end": END},
    )

    return graph.compile()


# Singleton agent instance (compiled once at import time).
_agent = _build_agent()


# =============================================================================
# Public API
# =============================================================================


def run_agent(question: str, db_path: str | None = None) -> dict[str, Any]:
    """Run the trial-and-error agent on a natural-language question.

    Args:
        question: The user's question in plain English.
        db_path:  Optional override for the database path.

    Returns:
        A dictionary with keys:
            success     -- bool
            sql         -- final SQL string (may be empty on failure)
            data        -- list of row dicts
            explanation -- plain-English summary
            attempts    -- number of LLM invocations used
            agent_log   -- list of step dicts for the UI
            error       -- error string (empty on success)
    """
    from nltosql.config import DB_PATH as default_db_path

    effective_path = db_path or default_db_path
    schema_ddl = get_schema_ddl(effective_path)

    if not schema_ddl:
        return {
            "success": False,
            "sql": "",
            "data": [],
            "explanation": "",
            "attempts": 0,
            "agent_log": [
                _log_entry("error", "error",
                           "No database schema found. Please check the database path.")
            ],
            "error": "No database schema found.",
        }

    initial_state: AgentState = {
        "question": question,
        "schema_ddl": schema_ddl,
        "generated_sql": "",
        "sql_valid": False,
        "execution_success": False,
        "results": [],
        "error_message": "",
        "attempt": 0,
        "max_attempts": MAX_RETRIES,
        "agent_log": [],
        "explanation": "",
        "db_path": effective_path,
    }

    try:
        final = _agent.invoke(initial_state)
    except Exception as exc:
        return {
            "success": False,
            "sql": "",
            "data": [],
            "explanation": "",
            "attempts": 0,
            "agent_log": [
                _log_entry("error", "error", f"Agent error: {exc}")
            ],
            "error": str(exc),
        }

    return {
        "success": final.get("execution_success", False),
        "sql": final.get("generated_sql", ""),
        "data": final.get("results", []),
        "explanation": final.get("explanation", ""),
        "attempts": final.get("attempt", 0),
        "agent_log": final.get("agent_log", []),
        "error": final.get("error_message", "") if not final.get("execution_success") else "",
    }


# =============================================================================
# Helpers
# =============================================================================


def _log_entry(
    step: str,
    status: str,
    message: str,
    **extra: Any,
) -> dict[str, Any]:
    """Create a structured log entry for the agent activity trace."""
    entry: dict[str, Any] = {
        "step": step,
        "status": status,
        "message": message,
        "timestamp": time.time(),
    }
    entry.update(extra)
    return entry
