# NL-to-SQL with LangGraph Trial-and-Error Agent

Convert natural-language questions into SQL queries using an AI agent that
**generates, executes, and self-corrects** -- all running locally with Ollama.

---

## Features

- **Trial-and-error agent** -- automatically diagnoses SQL errors and retries
  (configurable, default 3 attempts).
- **Safe by design** -- read-only database connections; blocks all destructive SQL
  operations (DROP, DELETE, INSERT, UPDATE, ...).
- **Fully local** -- no cloud APIs required.  Runs on your machine with Ollama.
- **Transparent reasoning** -- every step the agent takes is logged and visible
  in the UI.

## Tech Stack

| Component        | Technology                      |
|------------------|---------------------------------|
| Agent framework  | LangGraph 1.x                   |
| LLM              | Qwen 3.5 (2B) via Ollama        |
| UI               | Streamlit                        |
| Database         | SQLite                           |
| Language         | Python 3.13                      |

---

## Project Structure

```
nltosql/
├── src/
│   └── nltosql/                # Application package
│       ├── __init__.py
│       ├── agent.py            # LangGraph trial-and-error agent
│       ├── config.py           # Runtime settings (env vars)
│       ├── db_manager.py       # SQLite connection and query helpers
│       ├── prompts.py          # LLM prompt templates
│       ├── schema_extractor.py # Database DDL extraction
│       └── sql_validator.py    # SQL safety and syntax validation
├── scripts/
│   └── create_sample_db.py     # One-time script to seed demo data
├── data/
│   └── sample.db               # Sample e-commerce database (generated)
├── app.py                      # Streamlit UI (entry point)
├── pyproject.toml              # Package metadata and build config
├── requirements.txt            # Pinned Python dependencies
├── .env                        # Local environment overrides (not committed)
├── .env.example                # Template for .env
├── .gitignore
└── README.md
```

---

## Getting Started

### Prerequisites

| Requirement     | Version   | Notes                                    |
|-----------------|-----------|------------------------------------------|
| Python          | >= 3.11   | 3.13 recommended                         |
| Ollama          | latest    | https://ollama.com                       |
| Disk space      | ~3.5 GB   | For the Qwen 3.5 4B model weights       |

### Setup

```bash
# 1. Clone the repository
git clone <repo-url> nltosql
cd nltosql

# 2. Create and activate a virtual environment
python3.13 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# 3. Install the project in editable mode (includes all dependencies)
pip install -e .

# 4. Pull the LLM model (~3.5 GB download)
ollama pull qwen3.5:4b

# 5. Create the sample database
python scripts/create_sample_db.py

# 6. Copy and (optionally) edit environment variables
cp .env.example .env

# 7. Start the application
streamlit run app.py
```

The Streamlit UI will open at **http://localhost:8501**.

---

## How the Agent Works

```
Question --> Generate SQL --> Validate --> Execute --> Explain --> Done
                  ^                           |
                  +------ Fix (on error) <----+
```

1. **Generate** -- the LLM creates a SQL query from the question and database
   schema.
2. **Validate** -- safety checks (no DROP/DELETE) and syntax validation via
   SQLite EXPLAIN.
3. **Execute** -- the query runs against the database in read-only mode.
4. **On error** -- the error message is fed back to the LLM together with the
   failing SQL; a corrected query is generated and the cycle repeats.
5. **On success** -- the LLM produces a plain-English summary of the results.

---

## Configuration

All settings are read from environment variables (or a `.env` file).

| Variable          | Default                        | Description                        |
|-------------------|--------------------------------|------------------------------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434`       | Ollama server address              |
| `OLLAMA_MODEL`    | `qwen3.5:4b`                   | Model tag to use                   |
| `MAX_RETRIES`     | `3`                            | Maximum correction attempts        |
| `DB_PATH`         | `data/sample.db`               | Path to the SQLite database        |
| `TEMPERATURE`     | `0`                            | LLM temperature (0 = deterministic)|

---

## Using Your Own Database

You can point the application at any SQLite database:

1. **Via config** -- set `DB_PATH` in `.env` to the path of your `.db` file.
2. **Via the UI** -- use the file uploader in the Streamlit sidebar.

---

## Example Queries

Try these with the bundled sample e-commerce database:

- *Show me all customers from New York*
- *What are the top 5 most expensive products?*
- *How many orders were placed each month?*
- *Which customers have spent the most money?*
- *What is the average rating for each product category?*

---

## License

MIT
