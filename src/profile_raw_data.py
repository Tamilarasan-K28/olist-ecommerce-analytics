"""
profile_raw_data.py
Step 2 of Module 1: measure data quality of the nine raw Olist tables.

Run from the project root:
    python src/profile_raw_data.py

Reads data/raw/ (never modifies it) and writes aggregate-only CSV reports to
reports/data_quality/. No raw text (e.g. review comments) is written out.
"""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUT_DIR = PROJECT_ROOT / "reports" / "data_quality"
DT_FORMAT = "%Y-%m-%d %H:%M:%S"

FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "translation": "product_category_name_translation.csv",
}

# (table, columns that SHOULD identify one row)
KEY_CHECKS = [
    ("customers", ["customer_id"]),
    ("customers", ["customer_unique_id"]),   # a person, may repeat across orders
    ("orders", ["order_id"]),
    ("order_items", ["order_id", "order_item_id"]),
    ("payments", ["order_id", "payment_sequential"]),
    ("reviews", ["review_id"]),
    ("reviews", ["review_id", "order_id"]),
    ("products", ["product_id"]),
    ("sellers", ["seller_id"]),
    ("translation", ["product_category_name"]),
    ("geolocation", ["geolocation_zip_code_prefix"]),  # expected NOT unique
]

# (child table, child column, parent table, parent column)
RELATIONSHIPS = [
    ("orders", "customer_id", "customers", "customer_id"),
    ("order_items", "order_id", "orders", "order_id"),
    ("order_items", "product_id", "products", "product_id"),
    ("order_items", "seller_id", "sellers", "seller_id"),
    ("payments", "order_id", "orders", "order_id"),
    ("reviews", "order_id", "orders", "order_id"),
    ("products", "product_category_name", "translation", "product_category_name"),
    ("customers", "customer_zip_code_prefix", "geolocation", "geolocation_zip_code_prefix"),
    ("sellers", "seller_zip_code_prefix", "geolocation", "geolocation_zip_code_prefix"),
]

# (parent table, parent column, child table, child column): parents with no children
COVERAGE = [
    ("orders", "order_id", "order_items", "order_id"),
    ("orders", "order_id", "payments", "order_id"),
    ("orders", "order_id", "reviews", "order_id"),
    ("customers", "customer_id", "orders", "customer_id"),
    ("products", "product_id", "order_items", "product_id"),
    ("sellers", "seller_id", "order_items", "seller_id"),
]

ORDER_DATE_COLS = [
    "order_purchase_timestamp", "order_approved_at",
    "order_delivered_carrier_date", "order_delivered_customer_date",
    "order_estimated_delivery_date",
]
DATE_COLUMNS = {
    "orders": ORDER_DATE_COLS,
    "order_items": ["shipping_limit_date"],
    "reviews": ["review_creation_date", "review_answer_timestamp"],
}
NUMERIC_COLUMNS = {
    "order_items": ["order_item_id", "price", "freight_value"],
    "payments": ["payment_sequential", "payment_installments", "payment_value"],
    "reviews": ["review_score"],
    "products": ["product_name_lenght", "product_description_lenght",
                 "product_photos_qty", "product_weight_g", "product_length_cm",
                 "product_height_cm", "product_width_cm"],
    "geolocation": ["geolocation_lat", "geolocation_lng"],
}
CATEGORICAL_COLUMNS = [
    ("orders", "order_status"),
    ("payments", "payment_type"),
    ("reviews", "review_score"),
    ("customers", "customer_state"),
    ("sellers", "seller_state"),
]
ZIP_COLUMNS = [
    ("customers", "customer_zip_code_prefix"),
    ("sellers", "seller_zip_code_prefix"),
    ("geolocation", "geolocation_zip_code_prefix"),
]


def is_blank(s: pd.Series) -> pd.Series:
    """True where a text value is empty or only spaces."""
    return s.str.strip() == ""


def load_tables() -> dict:
    tables = {}
    for name, filename in FILES.items():
        path = RAW_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing raw file: {path}")
        # dtype=str + keep_default_na=False: see values exactly as stored.
        tables[name] = pd.read_csv(path, dtype=str, keep_default_na=False)
    return tables


def table_summary(tables):
    return pd.DataFrame([
        {"table": t, "rows": len(df), "columns": df.shape[1],
         "fully_duplicated_rows": int(df.duplicated().sum())}
        for t, df in tables.items()
    ])


def column_profile(tables):
    rows = []
    for t, df in tables.items():
        n = len(df)
        for c in df.columns:
            s = df[c]
            blank = is_blank(s)
            rows.append({
                "table": t, "column": c, "rows": n,
                "blank_count": int(blank.sum()),
                "blank_pct": round(100 * blank.sum() / n, 3),
                "distinct_non_blank": int(s[~blank].nunique()),
                "whitespace_padded_values": int((s != s.str.strip()).sum()),
            })
    return pd.DataFrame(rows)


def key_uniqueness(tables):
    rows = []
    for table, cols in KEY_CHECKS:
        df = tables[table]
        n = len(df)
        distinct = len(df.drop_duplicates(subset=cols))
        blank_rows = int(pd.concat([is_blank(df[c]) for c in cols], axis=1)
                         .any(axis=1).sum())
        rows.append({
            "table": table, "key": "+".join(cols), "rows": n,
            "distinct_keys": distinct,
            "extra_rows_beyond_first": n - distinct,
            "rows_in_duplicate_groups": int(df.duplicated(subset=cols, keep=False).sum()),
            "rows_with_blank_key": blank_rows,
            "is_unique": (n == distinct and blank_rows == 0),
        })
    return pd.DataFrame(rows)


def referential_integrity(tables):
    rows = []
    for child, ccol, parent, pcol in RELATIONSHIPS:
        c = tables[child][ccol]
        c = c[~is_blank(c)]
        parent_keys = set(tables[parent][pcol])
        distinct_child = c.drop_duplicates()
        rows.append({
            "relationship": f"{child}.{ccol} -> {parent}.{pcol}",
            "child_rows_checked": len(c),
            "orphan_rows": int((~c.isin(parent_keys)).sum()),
            "distinct_child_keys": len(distinct_child),
            "distinct_orphan_keys": int((~distinct_child.isin(parent_keys)).sum()),
        })
    return pd.DataFrame(rows)


def parent_coverage(tables):
    rows = []
    for parent, pcol, child, ccol in COVERAGE:
        p = tables[parent][pcol].drop_duplicates()
        child_keys = set(tables[child][ccol])
        missing = int((~p.isin(child_keys)).sum())
        rows.append({
            "parent": f"{parent}.{pcol}", "child": f"{child}.{ccol}",
            "distinct_parent_keys": len(p),
            "parents_without_child_rows": missing,
            "pct_without_child_rows": round(100 * missing / len(p), 3),
        })
    return pd.DataFrame(rows)


def orders_without_items_by_status(tables):
    orders = tables["orders"]
    with_items = set(tables["order_items"]["order_id"])
    no_items = orders[~orders["order_id"].isin(with_items)]
    return (no_items["order_status"].value_counts()
            .rename_axis("order_status")
            .reset_index(name="orders_without_items"))


def zip_length_profile(tables):
    rows = []
    for t, c in ZIP_COLUMNS:
        for length, cnt in tables[t][c].str.len().value_counts().sort_index().items():
            rows.append({"table": t, "column": c,
                         "string_length": int(length), "rows": int(cnt)})
    return pd.DataFrame(rows)


def date_profile(tables):
    rows = []
    for t, cols in DATE_COLUMNS.items():
        for c in cols:
            s = tables[t][c]
            nonblank = s[~is_blank(s)]
            parsed = pd.to_datetime(nonblank, format=DT_FORMAT, errors="coerce")
            rows.append({
                "table": t, "column": c, "rows": len(s),
                "blank_count": int(len(s) - len(nonblank)),
                "unparseable_count": int(parsed.isna().sum()),
                "min_date": parsed.min(), "max_date": parsed.max(),
            })
    return pd.DataFrame(rows)


def parsed_orders(tables):
    o = tables["orders"].copy()
    for c in ORDER_DATE_COLS:
        o[c] = pd.to_datetime(o[c].where(~is_blank(o[c])),
                              format=DT_FORMAT, errors="coerce")
    return o


def order_date_logic(o):
    checks = {
        "approved_before_purchase":
            o["order_approved_at"] < o["order_purchase_timestamp"],
        "carrier_date_before_approved":
            o["order_delivered_carrier_date"] < o["order_approved_at"],
        "customer_delivery_before_carrier":
            o["order_delivered_customer_date"] < o["order_delivered_carrier_date"],
        "customer_delivery_before_purchase":
            o["order_delivered_customer_date"] < o["order_purchase_timestamp"],
        "estimated_delivery_before_purchase":
            o["order_estimated_delivery_date"] < o["order_purchase_timestamp"],
    }
    return pd.DataFrame([{"check": k, "orders_violating": int(v.sum())}
                         for k, v in checks.items()])


def status_vs_missing_dates(o):
    miss = o[ORDER_DATE_COLS].isna().add_prefix("missing_")
    miss["order_status"] = o["order_status"]
    out = miss.groupby("order_status").sum()
    out.insert(0, "orders", o.groupby("order_status").size())
    return out.reset_index()


def numeric_profile(tables):
    rows = []
    for t, cols in NUMERIC_COLUMNS.items():
        for c in cols:
            s = tables[t][c]
            nonblank = s[~is_blank(s)]
            num = pd.to_numeric(nonblank, errors="coerce")
            valid = num.dropna()
            rows.append({
                "table": t, "column": c, "non_blank": len(nonblank),
                "non_numeric": int(num.isna().sum()),
                "min": valid.min(), "median": valid.median(),
                "mean": round(valid.mean(), 4), "max": valid.max(),
                "zeros": int((valid == 0).sum()),
                "negatives": int((valid < 0).sum()),
            })
    return pd.DataFrame(rows)


def categorical_counts(tables):
    rows = []
    for t, c in CATEGORICAL_COLUMNS:
        vc = tables[t][c].value_counts(dropna=False)
        total = int(vc.sum())
        for value, cnt in vc.items():
            rows.append({"table": t, "column": c, "value": value,
                         "count": int(cnt), "pct": round(100 * cnt / total, 3)})
    return pd.DataFrame(rows)


def check_against_manifest(summary):
    """Cross-check row counts with the Step 1 manifest."""
    path = OUT_DIR / "raw_data_manifest.csv"
    if not path.exists():
        return ["Manifest not found; skipped cross-check."]
    manifest = pd.read_csv(path).set_index("file")["row_count"]
    msgs = []
    for _, r in summary.iterrows():
        expected = manifest.get(FILES[r["table"]])
        if expected != r["rows"]:
            msgs.append(f"ROW COUNT MISMATCH {r['table']}: step1={expected}, now={r['rows']}")
    return msgs or ["Row counts match the Step 1 manifest."]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        tables = load_tables()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        return 1

    orders = parsed_orders(tables)
    reports = {
        "table_summary": table_summary(tables),
        "column_profile": column_profile(tables),
        "key_uniqueness": key_uniqueness(tables),
        "referential_integrity": referential_integrity(tables),
        "parent_coverage": parent_coverage(tables),
        "orders_without_items_by_status": orders_without_items_by_status(tables),
        "zip_length_profile": zip_length_profile(tables),
        "date_profile": date_profile(tables),
        "order_date_logic": order_date_logic(orders),
        "status_vs_missing_dates": status_vs_missing_dates(orders),
        "numeric_profile": numeric_profile(tables),
        "categorical_counts": categorical_counts(tables),
    }
    for name, df in reports.items():
        df.to_csv(OUT_DIR / f"profile_{name}.csv", index=False)

    for title in ["table_summary", "key_uniqueness", "referential_integrity",
                  "parent_coverage", "orders_without_items_by_status",
                  "order_date_logic", "status_vs_missing_dates"]:
        print(f"\n=== {title} ===")
        print(reports[title].to_string(index=False))

    print("\n=== cross-check ===")
    for m in check_against_manifest(reports["table_summary"]):
        print(m)
    print(f"\nReports written to: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())