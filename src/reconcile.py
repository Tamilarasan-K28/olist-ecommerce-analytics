"""
reconcile.py
Step 6 of Module 1: independent reconciliation.

Recomputes key figures straight from the raw CSVs using code that does NOT
import clean_data.py, then compares them with data/processed/.

Run from the project root:
    python src/reconcile.py
Exit code 0 only if every check passes. Reads only; modifies nothing.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
REPORT = ROOT / "reports" / "data_quality" / "reconciliation_report.csv"

RESULTS = []


def record(name, raw_value, cleaned_value, tolerance=0.0):
    ok = abs(float(raw_value) - float(cleaned_value)) <= tolerance
    RESULTS.append({"check": name, "from_raw": raw_value,
                    "from_cleaned": cleaned_value,
                    "tolerance": tolerance, "status": "PASS" if ok else "FAIL"})


def raw_csv(name, **kw):
    return pd.read_csv(RAW / name, dtype=str, keep_default_na=False, **kw)


def main() -> int:
    try:
        r_orders = raw_csv("olist_orders_dataset.csv")
        r_items = raw_csv("olist_order_items_dataset.csv")
        r_pay = raw_csv("olist_order_payments_dataset.csv")
        r_rev = raw_csv("olist_order_reviews_dataset.csv")
        r_cust = raw_csv("olist_customers_dataset.csv")
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        return 1

    c_orders = pd.read_csv(PROC / "orders_clean.csv")
    c_fin = pd.read_csv(PROC / "order_financials_clean.csv")
    c_items = pd.read_csv(PROC / "order_items_clean.csv")
    c_pbo = pd.read_csv(PROC / "payments_by_order_clean.csv")
    c_orev = pd.read_csv(PROC / "order_reviews_clean.csv")

    # 1. Row counts
    record("orders rows", len(r_orders), len(c_orders))
    record("order_items rows", len(r_items), len(c_items))

    # 2. Revenue: plain loop over raw text, independent of the pandas pipeline
    excluded = {o for o, s in zip(r_orders["order_id"], r_orders["order_status"])
                if s in ("canceled", "unavailable")}
    revenue = 0.0
    for oid, price in zip(r_items["order_id"], r_items["price"]):
        if oid not in excluded:
            revenue += float(price)
    record("total revenue (sum of price, non-canceled/unavailable)",
           round(revenue, 2), round(c_fin["revenue"].sum(), 2), tolerance=0.01)

    # 3. Revenue-eligible order count
    eligible = {o for o in r_items["order_id"] if o not in excluded}
    record("revenue-eligible orders", len(eligible),
           int(c_fin["is_revenue_eligible"].sum()))

    # 4. Total freight and total paid (all rows, no filtering)
    record("total freight",
           round(sum(float(x) for x in r_items["freight_value"]), 2),
           round(c_fin["items_freight_total"].sum(), 2), tolerance=0.01)
    record("total payment value",
           round(sum(float(x) for x in r_pay["payment_value"]), 2),
           round(c_pbo["payment_total"].sum(), 2), tolerance=0.01)

    # 5. Delivered orders with a delivery date
    delivered_with_date = sum(
        1 for s, d in zip(r_orders["order_status"],
                          r_orders["order_delivered_customer_date"])
        if s == "delivered" and d.strip() != "")
    record("delivery-eligible orders", delivered_with_date,
           int(c_orders["delivery_metric_eligible"].sum()))

    # 6. Late deliveries: string comparison works because the format is ISO-like
    late = sum(
        1 for s, d, e in zip(r_orders["order_status"],
                             r_orders["order_delivered_customer_date"],
                             r_orders["order_estimated_delivery_date"])
        if s == "delivered" and d.strip() != "" and d > e)
    record("late delivered orders", late, int(c_orders["is_late"].sum()))

    # 7. Distinct customers (people) and distinct reviewed orders
    record("distinct customer_unique_id", r_cust["customer_unique_id"].nunique(),
           pd.read_csv(PROC / "customers_clean.csv")["customer_unique_id"].nunique())
    record("orders with a review", r_rev["order_id"].nunique(), len(c_orev))

    out = pd.DataFrame(RESULTS)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(REPORT, index=False)
    print(out.to_string(index=False))

    failed = int((out["status"] == "FAIL").sum())
    print(f"\n{len(out) - failed} passed, {failed} failed.")
    print(f"Report: {REPORT}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())