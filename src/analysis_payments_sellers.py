"""
analysis_payments_sellers.py: payment mix, seller concentration, category concentration.
Run: python -m src.analysis_payments_sellers
Revenue = sum of item price for non-canceled/unavailable orders (rule R18).
"""
import pandas as pd

from src.db import get_engine

ENGINE = get_engine()


def q(sql):
    return pd.read_sql_query(sql, ENGINE)


def concentration(df, label):
    """Share of revenue held by the top 1%, 10% and 20% of entities."""
    s = df["revenue"].astype(float).sort_values(ascending=False).reset_index(drop=True)
    total, n = s.sum(), len(s)
    print(f"\n{label}: {n:,} entities, total revenue {total:,.2f}")
    for pct in (0.01, 0.10, 0.20):
        k = max(1, int(round(n * pct)))
        print(f"  top {int(pct*100):>2}% ({k:,} entities) hold {100 * s.head(k).sum() / total:.1f}% of revenue")


def main():
    # 1. Payment mix (payment lines, all orders; vouchers/not_defined shown, not hidden)
    mix = q("""
        SELECT payment_type, COUNT(*) AS payment_lines,
               COUNT(DISTINCT order_id) AS orders,
               ROUND(SUM(payment_value), 2) AS value
        FROM analytics.fact_payments GROUP BY 1 ORDER BY value DESC""")
    mix["pct_of_value"] = (100 * mix["value"].astype(float) / mix["value"].astype(float).sum()).round(2)
    print("Payment mix:\n", mix.to_string(index=False))
    mix.to_csv("reports/payment_mix.csv", index=False)

    # 2. Order-level payment profile: installments and number of payment types
    prof = q("""
        SELECT COUNT(*) AS orders_with_payment,
               COUNT(*) FILTER (WHERE max_installments > 1) AS installment_orders,
               COUNT(*) FILTER (WHERE payment_rows > 1) AS multi_line_orders
        FROM analytics.fact_orders WHERE payment_rows IS NOT NULL""")
    print("\nPayment profile:\n", prof.to_string(index=False))

    # 3. Review score by dominant payment type (order's first payment line)
    rev = q("""
        SELECT p.payment_type, COUNT(*) AS orders,
               ROUND(AVG(o.order_review_score), 3) AS avg_score
        FROM analytics.fact_orders o
        JOIN analytics.fact_payments p ON p.order_id = o.order_id AND p.payment_sequential = 1
        WHERE o.order_review_score IS NOT NULL
        GROUP BY 1 ORDER BY orders DESC""")
    print("\nReview score by first payment type:\n", rev.to_string(index=False))
    rev.to_csv("reports/review_by_payment_type.csv", index=False)

    # 4. Concentration of sellers and categories
    sellers = q("SELECT seller_id, revenue FROM analytics.v_seller_performance")
    cats = q("SELECT category, revenue FROM analytics.v_category_sales")
    concentration(sellers, "Sellers")
    concentration(cats, "Categories")
    sellers.sort_values("revenue", ascending=False).head(20).to_csv(
        "reports/top_sellers.csv", index=False)


if __name__ == "__main__":
    main()