"""
ml_build_dataset.py: build the leakage-safe modelling table for late-delivery prediction.
Run: python -m src.ml_build_dataset
Writes data/processed/ml_dataset.csv (ignored by Git). One row per delivery-eligible order.
"""
from pathlib import Path

import pandas as pd

from src.db import get_engine

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "ml_dataset.csv"

SQL = """
WITH items AS (
    SELECT i.order_id,
           COUNT(*)                     AS n_items,
           COUNT(DISTINCT i.seller_id)  AS n_sellers,
           COUNT(DISTINCT i.product_id) AS n_products,
           SUM(i.price)                 AS price_total,
           SUM(i.freight_value)         AS freight_total,
           SUM(p.product_weight_g_clean) AS total_weight_g
    FROM analytics.fact_order_items i
    JOIN analytics.dim_products p USING (product_id)
    GROUP BY i.order_id
), first_item AS (
    SELECT i.order_id, i.seller_id, p.product_category_english AS category
    FROM analytics.fact_order_items i
    JOIN analytics.dim_products p USING (product_id)
    WHERE i.order_item_id = 1
), first_pay AS (
    SELECT order_id, payment_type AS first_payment_type
    FROM analytics.fact_payments WHERE payment_sequential = 1
)
SELECT o.order_id,
       o.order_purchase_timestamp AS purchase_ts,
       o.order_estimated_delivery_date AS estimated_ts,
       o.is_late,
       c.customer_state, s.seller_state, fi.category,
       it.n_items, it.n_sellers, it.n_products,
       it.price_total, it.freight_total, it.total_weight_g,
       fp.first_payment_type, o.max_installments, o.payment_rows
FROM analytics.fact_orders o
JOIN analytics.dim_customers c USING (customer_id)
JOIN items it       USING (order_id)
JOIN first_item fi  USING (order_id)
JOIN analytics.dim_sellers s ON s.seller_id = fi.seller_id
LEFT JOIN first_pay fp USING (order_id)
WHERE o.delivery_metric_eligible
"""

FEATURES = [
    "purchase_month", "purchase_dow", "purchase_hour", "estimated_days", "same_state",
    "customer_state", "seller_state", "category", "n_items", "n_sellers", "n_products",
    "price_total", "freight_total", "total_weight_g", "first_payment_type",
    "max_installments", "payment_rows",
]
FORBIDDEN = {"order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date",
             "delivery_days", "is_late", "order_review_score", "review_count",
             "flag_carrier_before_approval", "flag_delivery_before_carrier"}

SPLITS = [("train", "2017-01-01", "2018-03-01"),
          ("validation", "2018-03-01", "2018-06-01"),
          ("test", "2018-06-01", "2018-09-01")]


def main():
    df = pd.read_sql_query(SQL, get_engine())
    print("delivery-eligible orders joined:", len(df), "(expected 96,470)")
    assert df["order_id"].is_unique, "join multiplied rows"
    assert len(df) == 96470, "row count differs from Module 1"

    df["is_late"] = df["is_late"].astype(bool).astype(int)
    for c in ["price_total", "freight_total", "total_weight_g"]:
        df[c] = df[c].astype(float)
    df["purchase_ts"] = pd.to_datetime(df["purchase_ts"])
    df["estimated_ts"] = pd.to_datetime(df["estimated_ts"])
    df["purchase_month"] = df["purchase_ts"].dt.month
    df["purchase_dow"] = df["purchase_ts"].dt.dayofweek
    df["purchase_hour"] = df["purchase_ts"].dt.hour
    df["estimated_days"] = (df["estimated_ts"] - df["purchase_ts"]).dt.total_seconds() / 86400
    df["same_state"] = (df["customer_state"] == df["seller_state"]).astype(int)

    assert not (set(FEATURES) & FORBIDDEN), "a forbidden column is in the feature list"

    df["split"] = "outside_window"
    for name, start, end in SPLITS:
        df.loc[(df["purchase_ts"] >= start) & (df["purchase_ts"] < end), "split"] = name

    summary = (df.groupby("split")["is_late"]
               .agg(orders="size", late="sum", late_rate="mean").round(4))
    print("\nsplit summary:\n", summary.to_string())
    print("\nmissing values per feature:\n",
          df[FEATURES].isna().sum()[lambda s: s > 0].to_string() or "none")
    print("\nfeatures:", FEATURES)

    out = df[["order_id", "purchase_ts", "split", "is_late"] + FEATURES]
    out.to_csv(OUT, index=False)
    print("\nWrote", OUT, "|", len(out), "rows")


if __name__ == "__main__":
    main()