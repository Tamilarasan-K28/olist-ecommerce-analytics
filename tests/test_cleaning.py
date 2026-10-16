"""Unit tests for src/clean_data.py. Run: python -m pytest -v"""
import numpy as np
import pandas as pd
import pytest

from src import clean_data as cd

ORDER_COLS = ["order_id", "customer_id", "order_status", "order_purchase_timestamp",
              "order_approved_at", "order_delivered_carrier_date",
              "order_delivered_customer_date", "order_estimated_delivery_date"]


def make_orders():
    rows = [
        ("A", "c1", "delivered", "2018-01-01 10:00:00", "2018-01-01 11:00:00",
         "2018-01-02 10:00:00", "2018-01-05 10:00:00", "2018-01-10 00:00:00"),
        ("B", "c2", "delivered", "2018-01-01 10:00:00", "2018-01-01 11:00:00",
         "2018-01-02 10:00:00", "", "2018-01-10 00:00:00"),
        ("C", "c3", "canceled", "2018-01-01 10:00:00", "2018-01-01 11:00:00",
         "", "2018-01-05 10:00:00", "2018-01-10 00:00:00"),
        ("D", "c4", "delivered", "2018-02-01 09:00:00", "2018-02-01 12:00:00",
         "2018-02-01 10:00:00", "2018-02-05 10:00:00", "2018-02-10 00:00:00"),
        ("E", "c5", "shipped", "2018-03-01 09:00:00", "2018-03-01 10:00:00",
         "2018-03-02 10:00:00", "", "2018-03-10 00:00:00"),
        ("F", "c6", "delivered", "2018-04-01 10:00:00", "2018-04-01 11:00:00",
         "2018-04-02 10:00:00", "2018-04-20 10:00:00", "2018-04-10 00:00:00"),
    ]
    return pd.DataFrame(rows, columns=ORDER_COLS, dtype=str)


def make_items():
    return pd.DataFrame({"order_id": ["A", "B", "C", "D", "F"]}, dtype=str)


def make_payments():
    return pd.DataFrame({
        "order_id": ["o1", "o1", "o2"],
        "payment_sequential": ["1", "2", "1"],
        "payment_type": ["credit_card", "voucher", "not_defined"],
        "payment_installments": ["3", "1", "0"],
        "payment_value": ["50.00", "0.00", "10.00"],
    }, dtype=str)


def test_blank_to_null():
    df = pd.DataFrame({"a": ["x", "", "  "], "b": ["1", "2", "3"]})
    out = cd.blank_to_null(df)
    assert out["a"].isna().tolist() == [False, True, True]
    assert out["b"].tolist() == ["1", "2", "3"]


def test_orders_keep_all_rows_and_flags():
    o = cd.clean_orders(make_orders(), make_items(), make_payments()).set_index("order_id")
    assert len(o) == 6
    assert o.loc["D", "flag_carrier_before_approval"]
    assert not o.loc["A", "flag_carrier_before_approval"]
    assert o.loc["B", "flag_delivered_missing_delivery_date"]
    assert o.loc["C", "flag_canceled_with_delivery_date"]
    assert o.loc["E", "flag_no_items_unexplained"]
    assert not o.loc["E", "has_items"]


def test_delivery_metrics_only_for_eligible_orders():
    o = cd.clean_orders(make_orders(), make_items(), make_payments()).set_index("order_id")
    assert o.loc["A", "delivery_days"] == pytest.approx(4.0)
    assert not o.loc["A", "is_late"]
    assert o.loc["F", "is_late"]
    for oid in ["B", "C", "E"]:
        assert pd.isna(o.loc[oid, "delivery_days"])
        assert pd.isna(o.loc[oid, "is_late"])


def test_payment_flags_and_aggregation():
    p = cd.clean_payments(make_payments())
    assert p["flag_payment_type_not_defined"].tolist() == [False, False, True]
    assert p["flag_zero_payment_value"].tolist() == [False, True, False]
    by_order = cd.build_payments_by_order(p).set_index("order_id")
    assert len(by_order) == 2
    assert by_order.loc["o1", "payment_rows"] == 2
    assert by_order.loc["o1", "payment_total"] == pytest.approx(50.0)
    assert by_order.loc["o2", "has_not_defined_payment"]


def test_order_review_uses_latest_and_flags_conflict():
    reviews = pd.DataFrame({
        "review_id": ["r1", "r2", "r3"],
        "order_id": ["o1", "o1", "o2"],
        "review_score": ["1", "5", "4"],
        "review_comment_title": ["", "", ""],
        "review_comment_message": ["", "", ""],
        "review_creation_date": ["2018-01-01 00:00:00"] * 3,
        "review_answer_timestamp": ["2018-01-02 10:00:00", "2018-01-05 10:00:00",
                                    "2018-01-03 10:00:00"],
    }, dtype=str)
    r = cd.clean_reviews(reviews)
    assert len(r) == 3
    out = cd.build_order_reviews(r).set_index("order_id")
    assert out.loc["o1", "order_review_score"] == 5
    assert out.loc["o1", "review_count"] == 2
    assert out.loc["o1", "has_conflicting_scores"]
    assert not out.loc["o2", "has_conflicting_scores"]


def test_geolocation_median_and_flags():
    geo = pd.DataFrame({
        "geolocation_zip_code_prefix": ["01046", "01046", "01046", "99999"],
        "geolocation_lat": ["-23.5", "-23.6", "-23.7", "50.0"],
        "geolocation_lng": ["-46.6", "-46.6", "-46.6", "10.0"],
        "geolocation_city": ["sao paulo"] * 4,
        "geolocation_state": ["SP"] * 4,
    }, dtype=str)
    z = cd.build_geolocation_zip(geo).set_index("zip_code_prefix")
    assert len(z) == 2
    assert z.loc["01046", "lat"] == pytest.approx(-23.6)
    assert z.loc["01046", "sample_count"] == 3
    assert not z.loc["01046", "flag_outside_brazil_box"]
    assert z.loc["99999", "flag_outside_brazil_box"]


def test_product_category_sources():
    products = pd.DataFrame({
        "product_id": ["p1", "p2", "p3", "p4"],
        "product_category_name": ["beleza_saude", "pc_gamer", "", "mystery"],
        "product_name_lenght": ["10"] * 4, "product_description_lenght": ["10"] * 4,
        "product_photos_qty": ["1"] * 4, "product_weight_g": ["100"] * 4,
        "product_length_cm": ["10"] * 4, "product_height_cm": ["10"] * 4,
        "product_width_cm": ["10"] * 4,
    }, dtype=str)
    translation = pd.DataFrame({"product_category_name": ["beleza_saude"],
                                "product_category_name_english": ["health_beauty"]})
    p = cd.clean_products(products, translation).set_index("product_id")
    assert p.loc["p1", "category_source"] == "translation_table"
    assert p.loc["p1", "product_category_english"] == "health_beauty"
    assert p.loc["p2", "category_source"] == "manual"
    assert p.loc["p3", "category_source"] == "unknown"
    assert p.loc["p3", "product_category_english"] == "unknown"
    assert p.loc["p4", "category_source"] == "untranslated"


def test_validation_detects_duplicate_and_orphan():
    df = pd.DataFrame({"k": ["a", "a"]})
    assert cd.check_unique("t", df, ["k"])
    child = pd.DataFrame({"k": ["a", "z"]})
    parent = pd.DataFrame({"k": ["a"]})
    assert cd.check_fk("fk", child, "k", parent, "k")
    assert cd.check_fk("fk", child.iloc[:1], "k", parent, "k") == []