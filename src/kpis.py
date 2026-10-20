"""
kpis.py: compute every KPI in docs/kpi_definitions.md from the analytics schema.
Run: python -m src.kpis
Known values from earlier modules are checked; new values are printed for review.
"""
import pandas as pd

from src.db import get_engine

SQL = """
SELECT
  SUM(revenue)                                                   AS revenue,
  SUM(items_freight_total) FILTER (WHERE is_revenue_eligible)    AS freight,
  COUNT(*) FILTER (WHERE is_revenue_eligible)                    AS eligible_orders,
  COUNT(*) FILTER (WHERE delivery_metric_eligible)               AS delivered_metric,
  AVG(delivery_days) FILTER (WHERE delivery_metric_eligible)     AS avg_delivery_days,
  COUNT(*) FILTER (WHERE is_late)                                AS late_orders,
  AVG(order_review_score)                                        AS avg_review_score,
  COUNT(*) FILTER (WHERE order_review_score <= 2)                AS low_score_orders,
  COUNT(*) FILTER (WHERE order_review_score IS NOT NULL)         AS reviewed_orders
FROM analytics.fact_orders
"""
REPEAT_SQL = """
SELECT COUNT(*) AS people, COUNT(*) FILTER (WHERE orders > 1) AS repeat_people
FROM analytics.v_customer_orders
"""


def main():
    eng = get_engine()
    k = pd.read_sql_query(SQL, eng).iloc[0].astype(float)
    r = pd.read_sql_query(REPEAT_SQL, eng).iloc[0].astype(float)

    print(f"Revenue                 {k.revenue:,.2f}   (expected 13,494,400.74)")
    print(f"Freight (eligible)      {k.freight:,.2f}")
    print(f"AOV                     {k.revenue / k.eligible_orders:,.2f}")
    print(f"Delivered (metric)      {k.delivered_metric:,.0f}   (expected 96,470)")
    print(f"Avg delivery days       {k.avg_delivery_days:.2f}")
    print(f"Late rate               {100 * k.late_orders / k.delivered_metric:.2f}%   (late orders {k.late_orders:,.0f}, expected 7,826)")
    print(f"Avg review score        {k.avg_review_score:.3f}")
    print(f"Low-score share         {100 * k.low_score_orders / k.reviewed_orders:.2f}%")
    print(f"Repeat customer rate    {100 * r.repeat_people / r.people:.2f}%   (expected 3.12%)")

    assert round(k.revenue, 2) == 13494400.74, "revenue differs from Module 1"
    assert k.delivered_metric == 96470 and k.late_orders == 7826
    assert round(100 * r.repeat_people / r.people, 2) == 3.12
    print("\nAll known values match.")


if __name__ == "__main__":
    main()