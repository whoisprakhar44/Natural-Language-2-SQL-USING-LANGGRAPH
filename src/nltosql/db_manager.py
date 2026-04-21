"""
Database manager for SQLite operations.

Provides helpers to connect, execute queries, and inspect metadata.
All connections are opened in **read-only** mode to guarantee that
LLM-generated SQL can never mutate the underlying data.
"""

import os
import sqlite3
from typing import Any

from nltosql.config import DB_PATH


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Return a read-only SQLite connection.

    The ``?mode=ro`` URI parameter makes it physically impossible for any
    SQL statement to modify the database file, providing a safety net
    independent of the SQL validator.

    Args:
        db_path: Optional override for the database file path.

    Returns:
        A ``sqlite3.Connection`` with ``row_factory`` set to ``sqlite3.Row``.

    Raises:
        FileNotFoundError: If the resolved path does not exist on disk.
    """
    path = db_path or DB_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"Database not found: {path}")

    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def execute_query(sql: str, db_path: str | None = None) -> list[dict[str, Any]]:
    """Execute a SELECT query and return results as a list of dictionaries.

    Each row is represented as ``{column_name: value}`` so that it can be
    passed directly to ``pandas.DataFrame`` or Streamlit's ``st.dataframe``.

    Args:
        sql: The SQL query to execute.
        db_path: Optional override for the database file path.

    Returns:
        A list of row dictionaries.
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_tables(db_path: str | None = None) -> list[dict[str, Any]]:
    """Return metadata for every table in the database.

    Each entry contains the table name, row count, and a list of column
    descriptors (name, data type, primary-key flag).

    Args:
        db_path: Optional override for the database file path.

    Returns:
        A list of table-info dictionaries, sorted by table name.
    """
    path = db_path or DB_PATH
    if not os.path.exists(path):
        return []

    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables: list[dict[str, Any]] = []

        for (table_name,) in cursor.fetchall():
            col_cursor = conn.execute(f"PRAGMA table_info('{table_name}')")
            columns = [
                {
                    "name": row[1],
                    "type": row[2],
                    "pk": bool(row[5]),
                }
                for row in col_cursor.fetchall()
            ]

            count_cursor = conn.execute(f"SELECT COUNT(*) FROM '{table_name}'")
            row_count = count_cursor.fetchone()[0]

            tables.append(
                {"name": table_name, "row_count": row_count, "columns": columns}
            )

        return tables
    finally:
        conn.close()


def get_table_names(db_path: str | None = None) -> list[str]:
    """Return a flat list of table names (used by the SQL validator)."""
    return [t["name"] for t in get_tables(db_path)]


def get_column_names(table_name: str, db_path: str | None = None) -> list[str]:
    """Return column names for *table_name* (used by the SQL validator)."""
    for table in get_tables(db_path):
        if table["name"] == table_name:
            return [c["name"] for c in table["columns"]]
    return []
