"""check_db_connection.py: confirm Pandas sees the same numbers as SQL."""
import sys

from src.db import read_table

orders = read_table("fact_orders")
items = read_table("fact_order_items")

checks = [
    ("fact_orders rows", len(orders), 99441),
    ("fact_order_items rows", len(items), 112650),
    ("revenue (sum)", round(float(orders["revenue"].sum()), 2), 13494400.74),
    ("late delivered orders", int(orders["is_late"].fillna(False).sum()), 7826),
]
failed = 0
for name, got, expected in checks:
    ok = got == expected
    failed += not ok
    print(f"{name:25s} pandas={got:>14,} expected={expected:>14,} {'PASS' if ok else 'FAIL'}")
sys.exit(1 if failed else 0)