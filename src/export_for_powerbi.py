"""
export_for_powerbi.py: export analytics tables to data/powerbi/*.csv
Run: python -m src.export_for_powerbi
Checks row counts and revenue after export.
"""
from pathlib import Path

import pandas as pd

from src.db import read_table

OUT = Path(__file__).resolve().parents[1] / "data" / "powerbi"

TABLES = {
    "fact_orders": None,
    "fact_order_items": None,
    "dim_customers": ["customer_id", "customer_unique_id", "customer_state", "customer_city"],
    "dim_products": None,
    "dim_sellers": None,
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, cols in TABLES.items():
        df = read_table(name)
        if cols:
            df = df[cols]
        df.to_csv(OUT / f"{name}.csv", index=False)
        print(f"{name:18s} {len(df):>8,} rows, {df.shape[1]} columns")

    check = pd.read_csv(OUT / "fact_orders.csv")
    revenue = round(check["revenue"].sum(), 2)
    print("revenue in exported file:", f"{revenue:,.2f}")
    assert len(check) == 99441
    assert revenue == 13494400.74, "revenue differs from the reference"
    print("Export verified.")


if __name__ == "__main__":
    main()