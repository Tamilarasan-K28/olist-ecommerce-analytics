"""
investigate_pending_rules.py
Step 3 (part 2) of Module 1: measure the items that cleaning rules still depend on.

Run from the project root:
    python src/investigate_pending_rules.py

Reads data/raw/ (never modifies it). Aggregate output only.
Saved to reports/data_quality/investigation_pending_rules.txt
"""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUT_DIR = PROJECT_ROOT / "reports" / "data_quality"

# Approximate bounding box of Brazil (an assumption used only as a sanity check).
LAT_MIN, LAT_MAX = -34.0, 6.0
LNG_MIN, LNG_MAX = -74.0, -34.0

LINES = []


def emit(text=""):
    print(text)
    LINES.append(str(text))


def section(title):
    emit(f"\n=== {title} ===")


def read(filename, usecols=None):
    return pd.read_csv(RAW_DIR / filename, dtype=str,
                       keep_default_na=False, usecols=usecols)


def payment_checks(payments, orders):
    section("Q6: payment anomalies")
    p = payments.copy()
    p["payment_value"] = pd.to_numeric(p["payment_value"])
    p["payment_installments"] = pd.to_numeric(p["payment_installments"])

    emit("rows with payment_value == 0, by payment_type:")
    emit(p.loc[p["payment_value"] == 0, "payment_type"].value_counts().to_string())
    emit("\nrows with payment_installments == 0, by payment_type:")
    emit(p.loc[p["payment_installments"] == 0, "payment_type"].value_counts().to_string())

    nd = p[p["payment_type"] == "not_defined"].merge(
        orders[["order_id", "order_status"]], on="order_id", how="left")
    emit("\nnot_defined payment rows: payment_value summary and order status")
    emit(nd["payment_value"].describe().round(2).to_string())
    emit(nd["order_status"].value_counts().to_string())


def payment_vs_items(payments, items):
    section("Q7: per-order payment total vs item total (price + freight)")
    it = items.copy()
    it["line_total"] = pd.to_numeric(it["price"]) + pd.to_numeric(it["freight_value"])
    item_total = it.groupby("order_id")["line_total"].sum().rename("items")
    pay_total = (payments.assign(v=pd.to_numeric(payments["payment_value"]))
                 .groupby("order_id")["v"].sum().rename("paid"))
    both = pd.concat([item_total, pay_total], axis=1, join="inner")
    diff = (both["paid"] - both["items"]).abs()
    emit(f"orders with both items and payments: {len(both)}")
    for t in (0.01, 1, 10):
        emit(f"orders where |paid - items| > {t}: {int((diff > t).sum())}")


def geography_checks():
    section("Q8: coordinates and state codes")
    geo = read("olist_geolocation_dataset.csv",
               usecols=["geolocation_lat", "geolocation_lng", "geolocation_state"])
    lat = pd.to_numeric(geo["geolocation_lat"])
    lng = pd.to_numeric(geo["geolocation_lng"])
    emit(f"latitude range:  {lat.min():.4f} to {lat.max():.4f}")
    emit(f"longitude range: {lng.min():.4f} to {lng.max():.4f}")
    outside = ~lat.between(LAT_MIN, LAT_MAX) | ~lng.between(LNG_MIN, LNG_MAX)
    emit(f"geolocation rows outside the approximate Brazil box: {int(outside.sum())}")

    for filename, col, label in [
            ("olist_customers_dataset.csv", "customer_state", "customer"),
            ("olist_sellers_dataset.csv", "seller_state", "seller"),
            ("olist_geolocation_dataset.csv", "geolocation_state", "geolocation")]:
        s = read(filename, usecols=[col])[col]
        emit(f"\n{label} state values ({s.nunique()} distinct, "
             f"lengths {sorted(s.str.len().unique())}):")
        emit(" ".join(sorted(s.unique())))


def product_checks(products):
    section("Q9: product physical attributes")
    for c in ["product_weight_g", "product_length_cm",
              "product_height_cm", "product_width_cm"]:
        s = products[c]
        v = pd.to_numeric(s[s.str.strip() != ""])
        emit(f"{c}: blank={int((s.str.strip() == '').sum())}, zeros={int((v == 0).sum())}")


def main() -> int:
    try:
        payments = read("olist_order_payments_dataset.csv")
        orders = read("olist_orders_dataset.csv", usecols=["order_id", "order_status"])
        items = read("olist_order_items_dataset.csv",
                     usecols=["order_id", "price", "freight_value"])
        products = read("olist_products_dataset.csv")
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        return 1

    payment_checks(payments, orders)
    payment_vs_items(payments, items)
    geography_checks()
    product_checks(products)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "investigation_pending_rules.txt"
    out.write_text("\n".join(LINES), encoding="utf-8")
    print(f"\nSaved to: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())