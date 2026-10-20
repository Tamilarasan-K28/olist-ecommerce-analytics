"""
db.py: shared database helper for notebooks and scripts.
Reads connection settings from .env (never commit .env).
"""
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parents[1]

# Trend window decided in Module 2 (assumption A1).
TREND_START = "2017-01-01"
TREND_END = "2018-08-31"


def _load_env() -> dict:
    env = {}
    path = ROOT / ".env"
    if not path.exists():
        raise FileNotFoundError(".env not found; copy .env.example to .env")
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    if env.get("PGPASSWORD", "") in ("", "your_password_here"):
        raise ValueError("Set your real PGPASSWORD in .env")
    return env


def get_engine():
    env = _load_env()
    url = URL.create(
        "postgresql+psycopg2",
        username=env.get("PGUSER", "postgres"),
        password=env["PGPASSWORD"],
        host=env.get("PGHOST", "localhost"),
        port=int(env.get("PGPORT", "5432")),
        database=env.get("PGDATABASE", "olist"),
    )
    return create_engine(url)


def read_table(name: str, schema: str = "analytics") -> pd.DataFrame:
    """Load a whole table or view from PostgreSQL into a DataFrame."""
    return pd.read_sql_query(f"SELECT * FROM {schema}.{name}", get_engine())