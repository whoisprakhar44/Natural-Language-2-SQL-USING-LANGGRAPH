"""
Schema extractor for SQLite databases.

Reads the database structure (DDL) and converts it into plain text that
is injected directly into the LLM prompt.  This is the core of the
"No-RAG" approach -- instead of embedding the schema into a vector
store, we paste the full DDL into the prompt context window.
"""

import os
import sqlite3

from nltosql.config import DB_PATH


def get_schema_ddl(db_path: str | None = None) -> str:
    """Extract the full schema as ``CREATE TABLE`` statements.

    These DDL statements are what the LLM reads to understand which
    tables and columns are available when generating SQL.

    Args:
        db_path: Optional override for the database file path.

    Returns:
        A newline-separated string of ``CREATE TABLE ...;`` statements,
        or an empty string if the database does not exist.
    """
    path = db_path or DB_PATH
    if not os.path.exists(path):
        return ""

    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        cursor = conn.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type='table' AND sql IS NOT NULL "
            "ORDER BY name"
        )
        return "\n\n".join(row[0] + ";" for row in cursor.fetchall())
    finally:
        conn.close()


def get_schema_summary(db_path: str | None = None) -> str:
    """Return a compact, human-readable summary of the schema.

    Useful for quick display in the UI sidebar rather than full DDL.

    Example output::

        customers: id (INTEGER, PK), name (TEXT), email (TEXT)
        orders: id (INTEGER, PK), customer_id (INTEGER), total (REAL)

    Args:
        db_path: Optional override for the database file path.

    Returns:
        A multi-line summary string, or a fallback message when
        no database is loaded.
    """
    path = db_path or DB_PATH
    if not os.path.exists(path):
        return "No database loaded."

    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )

        lines: list[str] = []
        for (table_name,) in cursor.fetchall():
            col_cursor = conn.execute(f"PRAGMA table_info('{table_name}')")
            cols: list[str] = []
            for col in col_cursor.fetchall():
                label = f"{col[1]} ({col[2]}"
                if col[5]:  # primary-key flag
                    label += ", PK"
                label += ")"
                cols.append(label)
            lines.append(f"{table_name}: {', '.join(cols)}")

        return "\n".join(lines)
    finally:
        conn.close()


def get_all_table_columns(db_path: str | None = None) -> dict[str, list[str]]:
    """Map each table name to its list of column names.

    Used by the SQL validator to verify that referenced columns exist
    in the target database.

    Args:
        db_path: Optional override for the database file path.

    Returns:
        ``{"table_name": ["col1", "col2", ...], ...}``
    """
    path = db_path or DB_PATH
    if not os.path.exists(path):
        return {}

    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        result: dict[str, list[str]] = {}
        for (table_name,) in cursor.fetchall():
            col_cursor = conn.execute(f"PRAGMA table_info('{table_name}')")
            result[table_name] = [col[1] for col in col_cursor.fetchall()]
        return result
    finally:
        conn.close()
