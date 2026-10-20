"""
analysis_lateness_reviews.py: late vs on-time review scores, adjusted for mix.
Run: python -m src.analysis_lateness_reviews
Unit of analysis: delivery-eligible orders that have an order-level review score.
Category = category of item 1 of the order (author's assumption; orders can hold several categories).
"""
import pandas as pd

from src.db import get_engine

SQL = """
SELECT o.order_id, o.is_late, o.order_review_score, o.has_conflicting_scores,
       c.customer_state, p.product_category_english AS category
FROM analytics.fact_orders o
JOIN analytics.dim_customers c USING (customer_id)
LEFT JOIN analytics.fact_order_items i
       ON i.order_id = o.order_id AND i.order_item_id = 1
LEFT JOIN analytics.dim_products p ON p.product_id = i.product_id
WHERE o.delivery_metric_eligible AND o.order_review_score IS NOT NULL
"""
MIN_GROUP = 30  # each side (late / on time) needs at least this many orders


def adjusted_gap(df, by):
    """Average late-minus-on-time score gap across groups, weighted by late orders."""
    g = df.groupby([by, "is_late"])["order_review_score"].agg(["mean", "size"]).unstack("is_late")
    g = g.dropna()
    g = g[(g[("size", True)] >= MIN_GROUP) & (g[("size", False)] >= MIN_GROUP)]
    gap = g[("mean", True)] - g[("mean", False)]
    w = g[("size", True)]
    out = pd.DataFrame({"gap": gap, "late_orders": w, "on_time_orders": g[("size", False)]})
    return float((gap * w).sum() / w.sum()), int(w.sum()), len(g), out


def raw_gap(df):
    m = df.groupby("is_late")["order_review_score"].mean()
    return float(m[True] - m[False])


def main():
    df = pd.read_sql_query(SQL, get_engine())
    df["is_late"] = df["is_late"].astype(bool)
    df["order_review_score"] = df["order_review_score"].astype(float)
    print("orders analysed:", len(df), "(expected 95,824 from Q7)")
    assert df["order_id"].is_unique, "join to item 1 multiplied rows"

    print(f"\nraw gap (late - on time): {raw_gap(df):.3f}")
    for by in ("customer_state", "category"):
        gap, w, n, table = adjusted_gap(df, by)
        print(f"adjusted gap within {by}: {gap:.3f}  "
              f"(groups used: {n}, late orders covered: {w:,} of {int(df['is_late'].sum()):,})")
        if by == "customer_state":
            table.sort_values("gap").to_csv("reports/lateness_gap_by_state.csv")

    clean = df[~df["has_conflicting_scores"].fillna(False).astype(bool)]
    print(f"\nsensitivity: excluding orders with conflicting review scores "
          f"({len(df) - len(clean):,} removed): raw gap {raw_gap(clean):.3f}")


if __name__ == "__main__":
    main()