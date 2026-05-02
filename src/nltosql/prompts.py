"""
Prompt templates for the NL-to-SQL agent.

Each constant below is a template string that gets formatted with runtime
values (schema, question, error messages, etc.) before being sent to the LLM.

Optimised for small models (2B-4B parameters) running locally:
    - Minimal token count -- every word earns its place.
    - Schema is provided as compact JSON, not verbose DDL.
    - /no_think tag disables internal reasoning on qwen3 models,
      which saves significant generation time.

There are three distinct prompts (down from four -- the explanation
prompt was removed to eliminate a full LLM round-trip):

    SYSTEM_PROMPT      -- Injected as the system message on every LLM call.
    GENERATION_PROMPT  -- First attempt at SQL generation.
    CORRECTION_PROMPT  -- Subsequent retry attempts after an error.
"""

# -- System prompt -------------------------------------------------------------
# Tight, directive system prompt for a 2B model. No fluff.

SYSTEM_PROMPT = (
    "You are a SQLite SQL generator. "
    "Output ONLY a single SELECT query. "
    "No explanations. No markdown. No commentary.\n"
    "Rules: only SELECT/WITH. Use only tables and columns from the schema. "
    "Never DROP/DELETE/INSERT/UPDATE/ALTER/CREATE. "
    "CRITICAL: Never generate multiple statements separated by semicolons. "
    "If asked to summarize or count multiple tables, combine them into ONE query using UNION ALL."
)

# -- Generation prompt ---------------------------------------------------------
# Schema is compact JSON. /no_think disables qwen3 reasoning tokens.

GENERATION_PROMPT = (
    "Schema (JSON format):\n"
    "{schema}\n\n"
    "Question: {question}\n\n"
    "SQL:"
)

# -- Correction prompt ---------------------------------------------------------
# Minimal context for self-correction. No coaching tips -- the 2B model
# doesn't benefit from them and they add ~100 tokens of overhead.

CORRECTION_PROMPT = (
    "Schema:\n{schema}\n\n"
    "Question: {question}\n\n"
    "Previous SQL:\n{previous_sql}\n\n"
    "Error: {error}\n\n"
    "Fix the SQL. Check column names and use Foreign Keys (fks) for JOINs.\n"
    "Corrected SQL:"
)
