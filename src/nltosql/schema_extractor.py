"""
Schema extractor for SQLite databases.

Reads the database structure and converts it into a compact JSON
representation that is injected directly into the LLM prompt.  This is
the core of the "No-RAG" approach -- instead of embedding the schema into
a vector store, we paste the schema into the prompt context window.

The JSON format is significantly more token-efficient than raw DDL
(CREATE TABLE statements), which matters on small models running locally.
"""

import json
import os
import sqlite3

from nltosql.config import DB_PATH


def get_schema_json(db_path: str | None = None) -> str:
    """Extract the schema as a compact JSON string.

    This format strips away all DDL noise (AUTOINCREMENT, FOREIGN KEY
    declarations, CHECK constraints) and gives the LLM exactly what it
    needs: table names, column names, and data types.

    Example output::

        {"categories":{"cols":["id:INT","name:TEXT","description:TEXT"]},
         "orders":{"cols":["id:INT","customer_id:INT","total:REAL","status:TEXT","order_date:TEXT"]}}

    Args:
        db_path: Optional override for the database file path.

    Returns:
        A compact JSON string, or an empty string if the database
        does not exist.
    """
    path = db_path or DB_PATH
    if not os.path.exists(path):
        return ""

    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )

        schema: dict[str, dict] = {}
        for (table_name,) in cursor.fetchall():
            col_cursor = conn.execute(f"PRAGMA table_info('{table_name}')")
            cols: list[str] = []
            for col in col_cursor.fetchall():
                col_type = col[2].upper() if col[2] else "TEXT"
                col_type = col_type.replace("INTEGER", "INT")
                cols.append(f"{col[1]}:{col_type}")
            
            schema[table_name] = {"cols": cols}
            
            # Fetch foreign keys for better JOIN accuracy.
            fk_cursor = conn.execute(f"PRAGMA foreign_key_list('{table_name}')")
            fks = []
            for fk in fk_cursor.fetchall():
                # fk[3] = from column, fk[2] = target table, fk[4] = target column
                fks.append(f"{fk[3]}->{fk[2]}.{fk[4]}")
            if fks:
                schema[table_name]["fks"] = fks

        # Compact JSON -- no indentation, no unnecessary whitespace.
        return json.dumps(schema, separators=(",", ":"))
    finally:
        conn.close()


# Keep the DDL extractor available for backward compatibility, but
# the optimised path uses get_schema_json exclusively.

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
