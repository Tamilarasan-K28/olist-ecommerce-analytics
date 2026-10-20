"""
load_staging.py
Module 2, Step 3: load data/processed/*_clean.csv into the staging schema.

Run from the project root (venv active):
    python src/load_staging.py
Reads connection settings from .env (never commit .env).
Truncates each staging table before loading, so reruns are safe.
Exit code 0 only if every loaded row count equals the CSV row count.
"""
import csv
import os
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"

# staging table -> cleaned CSV file (columns are taken from the CSV header)
TABLES = {
    "customers": "customers_clean.csv",
    "orders": "orders_clean.csv",
    "order_items": "order_items_clean.csv",
    "products": "products_clean.csv",
    "sellers": "sellers_clean.csv",
    "geolocation_zip": "geolocation_zip_clean.csv",
    "order_financials": "order_financials_clean.csv",
    "payments": "payments_clean.csv",
    "order_reviews": "order_reviews_clean.csv",
    "reviews": "reviews_clean.csv",
    "payments_by_order": "payments_by_order_clean.csv",
    "category_translation": "category_translation_clean.csv",
}


def load_env() -> dict:
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


def csv_row_count(path: Path) -> int:
    with open(path, newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.reader(f)) - 1  # minus header


def main() -> int:
    try:
        env = load_env()
        conn = psycopg2.connect(
            host=env.get("PGHOST", "localhost"), port=env.get("PGPORT", "5432"),
            dbname=env.get("PGDATABASE", "olist"), user=env.get("PGUSER", "postgres"),
            password=env["PGPASSWORD"])
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    failures = 0
    with conn, conn.cursor() as cur:
        for table, filename in TABLES.items():
            path = PROC / filename
            if not path.exists():
                print(f"MISSING: {path}")
                failures += 1
                continue
            with open(path, newline="", encoding="utf-8") as f:
                header = next(csv.reader(f))
            cols = ", ".join(header)
            cur.execute(f"TRUNCATE staging.{table}")
            with open(path, "r", encoding="utf-8") as f:
                cur.copy_expert(
                    f"COPY staging.{table} ({cols}) FROM STDIN WITH (FORMAT csv, HEADER true)", f)
            cur.execute(f"SELECT COUNT(*) FROM staging.{table}")
            loaded = cur.fetchone()[0]
            expected = csv_row_count(path)
            status = "PASS" if loaded == expected else "FAIL"
            failures += status == "FAIL"
            print(f"{table:18s} csv={expected:>8,} db={loaded:>8,} {status}")
    conn.close()
    print(f"\n{'ALL LOADS MATCH' if not failures else str(failures) + ' PROBLEM(S)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())