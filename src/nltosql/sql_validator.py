"""
SQL validator -- safety and syntax checks before execution.

Every LLM-generated query passes through this module before it touches
the database.  If validation fails the structured error message is fed
back into the agent's correction prompt so the LLM can fix the query.

Validation pipeline (in order):
    1. Empty-query check
    2. Dangerous-operation check (DROP, DELETE, INSERT, ...)
    3. Multi-statement check (SQL-injection prevention)
    4. Statement-type check (only SELECT / WITH-CTE allowed)
    5. Syntax check via SQLite EXPLAIN
"""

import os
import re
import sqlite3
from dataclasses import dataclass

from nltosql.config import DB_PATH

# -- Validation result --------------------------------------------------------


@dataclass
class ValidationResult:
    """Structured outcome of a validation run.

    Attributes:
        is_valid: Whether the SQL passed all checks.
        error:    Human-readable explanation when ``is_valid`` is ``False``.
                  This string is included in the correction prompt so that
                  the LLM knows exactly what to fix.
    """

    is_valid: bool
    error: str = ""


# -- Blocked patterns ---------------------------------------------------------
# Each tuple is (regex_pattern, user-facing reason).

_DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    (r"\bDROP\b", "DROP statements are not allowed"),
    (r"\bDELETE\b", "DELETE statements are not allowed"),
    (r"\bINSERT\b", "INSERT statements are not allowed"),
    (r"\bUPDATE\b", "UPDATE statements are not allowed"),
    (r"\bALTER\b", "ALTER statements are not allowed"),
    (r"\bCREATE\b", "CREATE statements are not allowed"),
    (r"\bTRUNCATE\b", "TRUNCATE statements are not allowed"),
    (r"\bREPLACE\b", "REPLACE statements are not allowed"),
    (r"\bATTACH\b", "ATTACH is not allowed"),
    (r"\bDETACH\b", "DETACH is not allowed"),
    (r"\bLOAD_EXTENSION\b", "LOAD_EXTENSION is not allowed"),
    (r"\bPRAGMA\b", "PRAGMA statements are not allowed"),
]


# -- Public API ---------------------------------------------------------------


def validate_sql(sql: str, db_path: str | None = None) -> ValidationResult:
    """Run the full validation pipeline on a SQL string.

    Args:
        sql:     The raw SQL string (may include markdown fences).
        db_path: Optional override for the database file path.

    Returns:
        A ``ValidationResult`` indicating success or the specific error.
    """
    path = db_path or DB_PATH
    sql = clean_llm_sql(sql)

    if not sql:
        return ValidationResult(False, "Empty SQL query")

    # 1. Dangerous-operation check
    sql_upper = sql.upper()
    for pattern, reason in _DANGEROUS_PATTERNS:
        if re.search(pattern, sql_upper):
            return ValidationResult(False, f"Safety violation: {reason}")

    # 2. Multi-statement check
    statements = _split_statements(sql)
    if len(statements) > 1:
        return ValidationResult(
            False,
            "Multiple SQL statements detected. Only single SELECT queries are allowed.",
        )

    # 3. Statement-type check
    stripped = sql_upper.strip().lstrip("(")
    if not stripped.startswith("SELECT") and not stripped.startswith("WITH"):
        return ValidationResult(
            False,
            "Only SELECT queries (or WITH/CTE queries) are allowed.",
        )

    # 4. Syntax check via EXPLAIN
    if os.path.exists(path):
        syntax_result = _check_syntax(sql, path)
        if not syntax_result.is_valid:
            return syntax_result

    return ValidationResult(True)


def clean_llm_sql(sql: str) -> str:
    """Strip markdown code fences and trailing semicolons from LLM output.

    LLMs sometimes wrap their output in triple-backtick code blocks even
    when instructed not to.  This helper normalises the string so that
    downstream consumers receive clean SQL.

    Args:
        sql: Raw LLM output string.

    Returns:
        Cleaned SQL string.
    """
    sql = sql.strip()

    # Remove fenced code blocks.
    if sql.startswith("```"):
        lines = sql.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        sql = "\n".join(lines)

    return sql.strip().rstrip(";").strip()


# -- Internal helpers ---------------------------------------------------------


def _split_statements(sql: str) -> list[str]:
    """Split SQL by semicolons while respecting string literals.

    This avoids false positives when data values contain semicolons,
    and prevents multi-statement injection attacks.
    """
    statements: list[str] = []
    current: list[str] = []
    in_string = False
    string_char: str | None = None

    for char in sql:
        if char in ("'", '"') and not in_string:
            in_string = True
            string_char = char
        elif char == string_char and in_string:
            in_string = False
            string_char = None
        elif char == ";" and not in_string:
            stmt = "".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            continue
        current.append(char)

    remaining = "".join(current).strip()
    if remaining:
        statements.append(remaining)

    return statements


def _check_syntax(sql: str, db_path: str) -> ValidationResult:
    """Validate SQL syntax using SQLite's EXPLAIN without executing.

    EXPLAIN causes SQLite to parse and plan the query.  If the syntax
    is invalid an ``sqlite3.Error`` is raised, whose message is
    propagated back to the agent as a correction hint.
    """
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            conn.execute(f"EXPLAIN {sql}")
            return ValidationResult(True)
        except sqlite3.Error as exc:
            return ValidationResult(False, f"SQL syntax error: {exc}")
        finally:
            conn.close()
    except Exception:
        # If we cannot connect, skip the syntax check gracefully.
        return ValidationResult(True)
