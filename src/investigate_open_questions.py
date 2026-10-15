"""
investigate_open_questions.py
Step 3 of Module 1: follow up on anomalies found by profile_raw_data.py.

Run from the project root:
    python src/investigate_open_questions.py

Reads data/raw/ (never modifies it). Output is aggregate-only: counts and
category names, never review text. Also saved to
reports/data_quality/investigation_open_questions.txt
"""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUT_DIR = PROJECT_ROOT / "reports" / "data_quality"
DT_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_COLS = [
    "order_purchase_timestamp", "order_approved_at",
    "order_delivered_carrier_date", "order_delivered_customer_date",
    "order_estimated_delivery_date",
]

LINES = []


def emit(text=""):
    print(text)
    LINES.append(str(text))


def section(title):
    emit(f"\n=== {title} ===")


def read(filename, usecols=None):
    return pd.read_csv(RAW_DIR / filename, dtype=str,
                       keep_default_na=False, usecols=usecols)


def review_id_duplicates(reviews, orders, customers):
    section("Q1: review_id values appearing on more than one row")
    dup = reviews[reviews.duplicated("review_id", keep=False)]
    dup = dup.merge(orders[["order_id", "customer_id"]], on="order_id", how="left")
    dup = dup.merge(customers, on="customer_id", how="left")
    g = dup.groupby("review_id")
    s = pd.DataFrame({
        "rows": g.size(),
        "distinct_orders": g["order_id"].nunique(),
        "distinct_scores": g["review_score"].nunique(),
        "distinct_messages": g["review_comment_message"].nunique(),
        "distinct_creation_dates": g["review_creation_date"].nunique(),
        "distinct_people": g["customer_unique_id"].nunique(),
    })
    emit(f"review_ids appearing more than once: {len(s)}")
    emit("rows per duplicated review_id:")
    emit(s["rows"].value_counts().sort_index().to_string())
    for col, label in [("distinct_orders", "order"),
                       ("distinct_scores", "score"),
                       ("distinct_messages", "comment message"),
                       ("distinct_creation_dates", "creation date"),
                       ("distinct_people", "customer_unique_id")]:
        emit(f"groups where every row shares one {label}: {int((s[col] == 1).sum())}")


def multiple_reviews_per_order(reviews):
    section("Q2: orders with more than one review row")
    per_order = reviews.groupby("order_id").agg(
        reviews=("review_id", "size"),
        distinct_scores=("review_score", "nunique"))
    emit("review rows per order (orders with at least one review):")
    emit(per_order["reviews"].value_counts().sort_index().to_string())
    multi = per_order[per_order["reviews"] > 1]
    emit(f"orders with more than one review row: {len(multi)}")
    emit(f"  of those, orders whose reviews have differing scores: "
         f"{int((multi['distinct_scores'] > 1).sum())}")


def category_gaps(products, translation):
    section("Q3: product categories")
    cat = products["product_category_name"]
    blank = cat.str.strip() == ""
    emit(f"products with blank category: {int(blank.sum())}")
    known = set(translation["product_category_name"])
    missing = products[~blank & ~cat.isin(known)]
    emit(f"products whose category is absent from the translation table: {len(missing)}")
    emit("category name -> product count:")
    emit(missing["product_category_name"].value_counts().to_string())


def status_date_anomalies(orders):
    section("Q4: order status vs timestamps")
    o = orders.copy()
    for c in DATE_COLS:
        o[c] = pd.to_datetime(o[c].where(o[c].str.strip() != ""),
                              format=DT_FORMAT, errors="coerce")
    cust = "order_delivered_customer_date"
    delivered = o["order_status"] == "delivered"
    canceled = o["order_status"] == "canceled"
    emit(f"delivered orders WITH a customer delivery date: "
         f"{int((delivered & o[cust].notna()).sum())}")
    emit(f"delivered orders with NO customer delivery date: "
         f"{int((delivered & o[cust].isna()).sum())}")
    emit(f"canceled orders WITH a customer delivery date: "
         f"{int((canceled & o[cust].notna()).sum())}")

    early_carrier = o["order_delivered_carrier_date"] < o["order_approved_at"]
    hours = ((o["order_approved_at"] - o["order_delivered_carrier_date"])
             [early_carrier].dt.total_seconds() / 3600)
    emit(f"\ncarrier date earlier than approval: {int(early_carrier.sum())} orders")
    emit("gap in hours (approval minus carrier date):")
    emit(hours.describe().round(2).to_string())
    emit("their order_status:")
    emit(o.loc[early_carrier, "order_status"].value_counts().to_string())

    early_delivery = o[cust] < o["order_delivered_carrier_date"]
    days = ((o["order_delivered_carrier_date"] - o[cust])
            [early_delivery].dt.total_seconds() / 86400)
    emit(f"\ncustomer delivery earlier than carrier date: {int(early_delivery.sum())} orders")
    emit("gap in days (carrier date minus customer delivery date):")
    emit(days.describe().round(2).to_string())


def payment_shape(payments, orders):
    section("Q5: payments per order")
    per = payments.groupby("order_id").size()
    emit("payment rows per order -> number of orders:")
    emit(per.value_counts().sort_index().to_string())
    no_pay = orders[~orders["order_id"].isin(set(payments["order_id"]))]
    emit("\nstatus of orders with no payment row:")
    emit(no_pay["order_status"].value_counts().to_string())


def main() -> int:
    try:
        reviews = read("olist_order_reviews_dataset.csv")
        orders = read("olist_orders_dataset.csv")
        customers = read("olist_customers_dataset.csv",
                         usecols=["customer_id", "customer_unique_id"])
        products = read("olist_products_dataset.csv",
                        usecols=["product_id", "product_category_name"])
        translation = read("product_category_name_translation.csv")
        payments = read("olist_order_payments_dataset.csv")
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        return 1

    review_id_duplicates(reviews, orders, customers)
    multiple_reviews_per_order(reviews)
    category_gaps(products, translation)
    status_date_anomalies(orders)
    payment_shape(payments, orders)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "investigation_open_questions.txt"
    out.write_text("\n".join(LINES), encoding="utf-8")
    print(f"\nSaved to: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())