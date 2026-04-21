"""
Prompt templates for the NL-to-SQL agent.

Each constant below is a template string that gets formatted with runtime
values (schema, question, error messages, etc.) before being sent to the LLM.

There are four distinct prompts, each used at a different stage of the
agent's trial-and-error loop:

    SYSTEM_PROMPT      -- Injected as the system message on every LLM call.
    GENERATION_PROMPT  -- First attempt at SQL generation.
    CORRECTION_PROMPT  -- Subsequent retry attempts after an error.
    EXPLANATION_PROMPT -- Summarises the query results in plain English.
"""

# -- System prompt -------------------------------------------------------------
# Sets the LLM's role and hard constraints for every request.

SYSTEM_PROMPT = (
    "You are an expert SQLite SQL query generator.\n"
    "\n"
    "Rules:\n"
    "1. Generate ONLY valid SQLite SELECT queries.\n"
    "2. Output ONLY the SQL query -- no explanations, no markdown, no code fences.\n"
    "3. Use only tables and columns that exist in the provided schema.\n"
    "4. Use proper SQLite syntax and built-in functions.\n"
    "5. Prefer table aliases for readability.\n"
    "6. Handle NULL values appropriately.\n"
    "7. Never generate destructive queries "
    "(DROP, DELETE, INSERT, UPDATE, ALTER, CREATE).\n"
)

# -- Generation prompt ---------------------------------------------------------
# Used on the first attempt: schema + natural-language question --> SQL.

GENERATION_PROMPT = (
    "Given the following SQLite database schema:\n"
    "\n"
    "{schema}\n"
    "\n"
    "Write a SQL query to answer this question:\n"
    "{question}\n"
    "\n"
    "Remember: Output ONLY the raw SQL query. "
    "No explanations, no markdown formatting, no code fences."
)

# -- Correction prompt ---------------------------------------------------------
# Used on retry attempts.  Includes the previous (failing) SQL and the error
# message so that the LLM can diagnose and fix the issue.

CORRECTION_PROMPT = (
    "Given the following SQLite database schema:\n"
    "\n"
    "{schema}\n"
    "\n"
    "I asked you to answer this question:\n"
    "{question}\n"
    "\n"
    "You previously generated this SQL query:\n"
    "{previous_sql}\n"
    "\n"
    "But it produced this error:\n"
    "{error}\n"
    "\n"
    "Please analyse the error carefully and generate a CORRECTED SQL query.\n"
    "Common fixes:\n"
    "- Verify column names against the schema\n"
    "- Verify table names against the schema\n"
    "- Fix JOIN conditions\n"
    "- Fix GROUP BY clauses\n"
    "- Fix syntax errors\n"
    "\n"
    "Output ONLY the corrected SQL query. "
    "No explanations, no markdown formatting, no code fences."
)

# -- Explanation prompt --------------------------------------------------------
# Used after successful execution to produce a natural-language summary.

EXPLANATION_PROMPT = (
    "Given this question: {question}\n"
    "\n"
    "This SQL query was executed:\n"
    "{sql}\n"
    "\n"
    "And returned these results:\n"
    "{results}\n"
    "\n"
    "Provide a brief, clear, natural-language summary of the results.\n"
    "Keep it concise -- 2-3 sentences maximum.  Focus on the key insights.\n"
    "Do not include the SQL query in your explanation."
)
