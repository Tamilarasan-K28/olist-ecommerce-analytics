"""Integration tests on the analytics schema: keys, orphans, invalid values, reconciliation."""
import pytest
from sqlalchemy import text

from src.db import get_engine


@pytest.fixture(scope="module")
def conn():
    try:
        c = get_engine().connect()
    except Exception as exc:
        pytest.skip(f"database not available: {exc}")
    yield c
    c.close()


def one(conn, sql):
    return conn.execute(text(sql)).scalar()


COUNTS = {"fact_orders": 99441, "fact_order_items": 112650, "fact_payments": 103886,
          "fact_reviews": 99224, "dim_customers": 99441, "dim_products": 32951,
          "dim_sellers": 3095, "dim_geography": 19015}


@pytest.mark.parametrize("table,n", COUNTS.items())
def test_row_counts(conn, table, n):
    assert one(conn, f"SELECT COUNT(*) FROM analytics.{table}") == n


DUPES = {
    "orders": "SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM analytics.fact_orders",
    "items": "SELECT COUNT(*) FROM (SELECT 1 FROM analytics.fact_order_items GROUP BY order_id, order_item_id HAVING COUNT(*)>1) d",
    "payments": "SELECT COUNT(*) FROM (SELECT 1 FROM analytics.fact_payments GROUP BY order_id, payment_sequential HAVING COUNT(*)>1) d",
    "reviews": "SELECT COUNT(*) FROM (SELECT 1 FROM analytics.fact_reviews GROUP BY review_id, order_id HAVING COUNT(*)>1) d",
}
ORPHANS = {
    "items_orders": "SELECT COUNT(*) FROM analytics.fact_order_items i LEFT JOIN analytics.fact_orders o USING (order_id) WHERE o.order_id IS NULL",
    "items_products": "SELECT COUNT(*) FROM analytics.fact_order_items i LEFT JOIN analytics.dim_products p USING (product_id) WHERE p.product_id IS NULL",
    "items_sellers": "SELECT COUNT(*) FROM analytics.fact_order_items i LEFT JOIN analytics.dim_sellers s USING (seller_id) WHERE s.seller_id IS NULL",
    "payments_orders": "SELECT COUNT(*) FROM analytics.fact_payments p LEFT JOIN analytics.fact_orders o USING (order_id) WHERE o.order_id IS NULL",
    "reviews_orders": "SELECT COUNT(*) FROM analytics.fact_reviews r LEFT JOIN analytics.fact_orders o USING (order_id) WHERE o.order_id IS NULL",
    "orders_customers": "SELECT COUNT(*) FROM analytics.fact_orders o LEFT JOIN analytics.dim_customers c USING (customer_id) WHERE c.customer_id IS NULL",
}
INVALID = {
    "review_score_range": "SELECT COUNT(*) FROM analytics.fact_reviews WHERE review_score NOT BETWEEN 1 AND 5",
    "price_not_positive": "SELECT COUNT(*) FROM analytics.fact_order_items WHERE price <= 0",
    "negative_freight": "SELECT COUNT(*) FROM analytics.fact_order_items WHERE freight_value < 0",
    "negative_payment": "SELECT COUNT(*) FROM analytics.fact_payments WHERE payment_value < 0",
    "negative_delivery_days": "SELECT COUNT(*) FROM analytics.fact_orders WHERE delivery_days < 0",
}


@pytest.mark.parametrize("name", DUPES)
def test_no_duplicate_keys(conn, name):
    assert one(conn, DUPES[name]) == 0


@pytest.mark.parametrize("name", ORPHANS)
def test_no_orphans(conn, name):
    assert one(conn, ORPHANS[name]) == 0


@pytest.mark.parametrize("name", INVALID)
def test_no_invalid_values(conn, name):
    assert one(conn, INVALID[name]) == 0


def test_reconciled_totals(conn):
    assert round(float(one(conn, "SELECT SUM(revenue) FROM analytics.fact_orders")), 2) == 13494400.74
    assert round(float(one(conn, "SELECT SUM(payment_value) FROM analytics.fact_payments")), 2) == 16008872.12
    assert one(conn, "SELECT COUNT(*) FROM analytics.fact_orders WHERE is_late") == 7826
    assert one(conn, "SELECT COUNT(DISTINCT customer_unique_id) FROM analytics.dim_customers") == 96096


@pytest.mark.parametrize("view", ["v_monthly_sales", "v_category_sales", "v_seller_performance", "v_customer_orders"])
def test_view_revenue_totals(conn, view):
    assert round(float(one(conn, f"SELECT SUM(revenue) FROM analytics.{view}")), 2) == 13494400.74