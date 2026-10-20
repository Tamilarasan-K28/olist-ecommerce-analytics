"""
delivery_analysis.py: late rate by route type and by seller.
Run: python -m src.delivery_analysis
Writes reports/delivery_by_route.csv and reports/seller_late_rates.csv.
"""
import pandas as pd

from src.db import get_engine

MIN_SELLER_ORDERS = 50

SQL = """
SELECT o.order_id, o.delivery_days, o.is_late,
       c.customer_state, s.seller_id, s.seller_state,
       (SELECT COUNT(DISTINCT seller_id) FROM analytics.fact_order_items x
         WHERE x.order_id = o.order_id) AS n_sellers
FROM analytics.fact_orders o
JOIN analytics.dim_customers c USING (customer_id)
JOIN analytics.fact_order_items i ON i.order_id = o.order_id AND i.order_item_id = 1
JOIN analytics.dim_sellers s ON s.seller_id = i.seller_id
WHERE o.delivery_metric_eligible
"""


def main():
    df = pd.read_sql_query(SQL, get_engine())
    df["is_late"] = df["is_late"].astype(bool)
    df["delivery_days"] = df["delivery_days"].astype(float)
    print("orders analysed:", len(df), "(expected 96,470)")
    assert df["order_id"].is_unique
    print("orders with more than one seller:", int((df["n_sellers"] > 1).sum()))

    df["route"] = (df["customer_state"] == df["seller_state"]).map(
        {True: "same_state", False: "cross_state"})
    route = (df.groupby("route")
             .agg(orders=("order_id", "size"),
                  avg_delivery_days=("delivery_days", "mean"),
                  late_pct=("is_late", lambda s: 100 * s.mean()))
             .round(2).reset_index())
    print("\nBy route type:\n", route.to_string(index=False))
    route.to_csv("reports/delivery_by_route.csv", index=False)

    sel = (df.groupby("seller_id")
           .agg(orders=("order_id", "size"), late_orders=("is_late", "sum"),
                avg_delivery_days=("delivery_days", "mean"))
           .reset_index())
    sel["late_pct"] = (100 * sel["late_orders"] / sel["orders"]).round(2)
    big = sel[sel["orders"] >= MIN_SELLER_ORDERS].copy()
    print(f"\nsellers: {len(sel):,} total, {len(big):,} with >= {MIN_SELLER_ORDERS} orders "
          f"(covering {big['orders'].sum():,} of {len(df):,} orders)")
    print("late rate across those sellers (percentiles 10/50/90):",
          big["late_pct"].quantile([0.1, 0.5, 0.9]).round(2).tolist())

    big = big.sort_values("late_orders", ascending=False)
    top = big.head(20)
    total_late = int(df["is_late"].sum())
    print(f"\nthe 20 sellers with most late orders hold {int(top['late_orders'].sum()):,} "
          f"of {total_late:,} late orders ({100 * top['late_orders'].sum() / total_late:.1f}%)")
    print(f"... and handle {int(top['orders'].sum()):,} of {len(df):,} orders "
          f"({100 * top['orders'].sum() / len(df):.1f}%)")
    big.to_csv("reports/seller_late_rates.csv", index=False)


if __name__ == "__main__":
    main()