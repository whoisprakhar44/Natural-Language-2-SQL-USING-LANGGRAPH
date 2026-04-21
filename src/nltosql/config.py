"""
Application configuration module.

Centralises all runtime settings by reading from environment variables
with sensible defaults.  Values are loaded from a ``.env`` file at import
time via ``python-dotenv``, so no code changes are needed to customise
the application for different environments.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# -- Ollama LLM settings ------------------------------------------------------
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")
TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0"))

# -- Agent settings ------------------------------------------------------------
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

# -- Database settings ---------------------------------------------------------
DB_PATH: str = os.getenv("DB_PATH", "data/sample.db")
