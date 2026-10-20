"""
clean_data.py
Step 4 of Module 1: apply the documented cleaning rules (docs/cleaning_rules.md).

Run from the project root:
    python src/clean_data.py

Reads data/raw/ (never modifies it) and writes data/processed/.
Principle: flag problems, do not silently delete rows. Only geolocation is
reduced (to one row per zip), as decided in rule R8.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUT_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR = PROJECT_ROOT / "reports" / "data_quality"

DT_FORMAT = "%Y-%m-%d %H:%M:%S"
ORDER_DATE_COLS = [
    "order_purchase_timestamp", "order_approved_at",
    "order_delivered_carrier_date", "order_delivered_customer_date",
    "order_estimated_delivery_date",
]

# Approximate bounding box of Brazil (an assumption used only for flagging).
LAT_MIN, LAT_MAX = -34.0, 6.0
LNG_MIN, LNG_MAX = -74.0, -34.0

# The 26 Brazilian states plus the Federal District.
VALID_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}

# Rule R7: categories missing from the translation table.
# These English names are MANUAL translations by the project author.
MANUAL_CATEGORY_MAP = {
    "pc_gamer": "pc_gamer",
    "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_and_food_preparers",
}

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


# ---------- helpers ----------
def blank_to_null(df: pd.DataFrame) -> pd.DataFrame:
    """R1: empty or whitespace-only text becomes missing (NaN)."""
    out = df.copy()
    for c in out.columns:
        s = out[c]
        out[c] = s.where(s.str.strip() != "", np.nan)
    return out


def parse_datetimes(df: pd.DataFrame, cols) -> pd.DataFrame:
    """R2: parse timestamp text. Unparseable values become NaT."""
    out = df.copy()
    for c in cols:
        out[c] = pd.to_datetime(out[c], format=DT_FORMAT, errors="coerce")
    return out


def to_numeric(df: pd.DataFrame, cols) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


# ---------- table cleaners ----------
def clean_orders(orders, items, payments) -> pd.DataFrame:
    """R10, R11, R12, R13: keep every order, add flags and delivery fields."""
    o = parse_datetimes(blank_to_null(orders), ORDER_DATE_COLS)
    status = o["order_status"]
    carrier = o["order_delivered_carrier_date"]
    customer = o["order_delivered_customer_date"]

    o["has_items"] = o["order_id"].isin(set(items["order_id"]))
    o["has_payment"] = o["order_id"].isin(set(payments["order_id"]))

    o["flag_carrier_before_approval"] = carrier < o["order_approved_at"]
    o["flag_delivery_before_carrier"] = customer < carrier
    o["flag_delivered_missing_delivery_date"] = (status == "delivered") & customer.isna()
    o["flag_canceled_with_delivery_date"] = (status == "canceled") & customer.notna()
    o["flag_no_items_unexplained"] = (~o["has_items"]) & status.isin(["invoiced", "shipped"])

    # Delivery metrics only for delivered orders that have a delivery date.
    eligible = (status == "delivered") & customer.notna()
    o["delivery_metric_eligible"] = eligible
    days = (customer - o["order_purchase_timestamp"]).dt.total_seconds() / 86400
    o["delivery_days"] = days.where(eligible)
    late = (customer > o["order_estimated_delivery_date"]).astype("boolean")
    o["is_late"] = late.where(eligible)
    return o


def clean_order_items(items) -> pd.DataFrame:
    i = parse_datetimes(blank_to_null(items), ["shipping_limit_date"])
    return to_numeric(i, ["order_item_id", "price", "freight_value"])


def clean_payments(payments) -> pd.DataFrame:
    """R14, R15: flag unusual payments, change nothing."""
    p = to_numeric(blank_to_null(payments),
                   ["payment_sequential", "payment_installments", "payment_value"])
    p["flag_payment_type_not_defined"] = p["payment_type"] == "not_defined"
    p["flag_zero_payment_value"] = p["payment_value"] == 0
    p["flag_zero_installments"] = p["payment_installments"] == 0
    p["flag_zero_weight"] = p["product_weight_g"] == 0
    p["product_weight_g_clean"] = p["product_weight_g"].where(p["product_weight_g"] > 0)
    return p


def build_payments_by_order(p) -> pd.DataFrame:
    """R13: one row per order, so joins cannot multiply rows."""
    return p.groupby("order_id").agg(
        payment_rows=("payment_sequential", "size"),
        payment_total=("payment_value", "sum"),
        max_installments=("payment_installments", "max"),
        distinct_payment_types=("payment_type", "nunique"),
        has_not_defined_payment=("flag_payment_type_not_defined", "any"),
    ).reset_index()

def build_order_financials(orders, items, payments_by_order) -> pd.DataFrame:
    """R18: one row per order. Revenue = sum of item price for orders that are
    not canceled/unavailable. Payment total is kept only for reconciliation."""
    agg = items.groupby("order_id").agg(
        item_count=("order_item_id", "size"),
        items_price_total=("price", "sum"),
        items_freight_total=("freight_value", "sum")).reset_index()
    f = orders[["order_id", "order_status"]].merge(agg, on="order_id", how="left")
    f = f.merge(payments_by_order[["order_id", "payment_total"]],
                on="order_id", how="left")
    f["payment_minus_items"] = (
        f["payment_total"] - (f["items_price_total"] + f["items_freight_total"])
    ).round(2)
    both = f["items_price_total"].notna() & f["payment_total"].notna()
    f["flag_payment_item_mismatch"] = both & (f["payment_minus_items"].abs() > 0.01)
    f["is_revenue_eligible"] = (f["items_price_total"].notna()
                                & ~f["order_status"].isin(["canceled", "unavailable"]))
    f["revenue"] = f["items_price_total"].where(f["is_revenue_eligible"])
    return f


def clean_reviews(reviews) -> pd.DataFrame:
    """R4: keep every review row. Key is review_id + order_id."""
    r = parse_datetimes(blank_to_null(reviews),
                        ["review_creation_date", "review_answer_timestamp"])
    r["review_score"] = pd.to_numeric(r["review_score"], errors="coerce").astype("Int64")
    return r


def build_order_reviews(r) -> pd.DataFrame:
    """R5: one row per order. Score comes from the latest review."""
    ordered = r.sort_values(
        ["review_answer_timestamp", "review_creation_date", "review_id"],
        kind="mergesort")
    summary = ordered.groupby("order_id").agg(
        review_count=("review_id", "size"),
        distinct_scores=("review_score", "nunique")).reset_index()
    summary["has_conflicting_scores"] = summary["distinct_scores"] > 1
    latest = (ordered.drop_duplicates("order_id", keep="last")
              [["order_id", "review_id", "review_score"]]
              .rename(columns={"review_id": "selected_review_id",
                               "review_score": "order_review_score"}))
    return summary.merge(latest, on="order_id", how="left")


def build_geolocation_zip(geo) -> pd.DataFrame:
    """R8, R16: one row per zip using median coordinates.
    Zips whose median falls outside the Brazil box are flagged and their
    lat/lng set to missing; the raw medians are kept for transparency."""
    g = to_numeric(blank_to_null(geo), ["geolocation_lat", "geolocation_lng"])
    z = g.groupby("geolocation_zip_code_prefix").agg(
        lat=("geolocation_lat", "median"),
        lng=("geolocation_lng", "median"),
        sample_count=("geolocation_lat", "size")).reset_index()
    z = z.rename(columns={"geolocation_zip_code_prefix": "zip_code_prefix"})
    inside = z["lat"].between(LAT_MIN, LAT_MAX) & z["lng"].between(LNG_MIN, LNG_MAX)
    z["flag_outside_brazil_box"] = ~inside
    z["lat_median_raw"] = z["lat"]
    z["lng_median_raw"] = z["lng"]
    z.loc[~inside, ["lat", "lng"]] = np.nan
    return z


def clean_customers(customers, zip_set) -> pd.DataFrame:
    """R9, R17"""
    c = blank_to_null(customers)
    c["flag_zip_not_in_geolocation"] = ~c["customer_zip_code_prefix"].isin(zip_set)
    c["flag_invalid_state"] = ~c["customer_state"].isin(VALID_STATES)
    return c


def clean_sellers(sellers, zip_set) -> pd.DataFrame:
    """R9, R17"""
    s = blank_to_null(sellers)
    s["flag_zip_not_in_geolocation"] = ~s["seller_zip_code_prefix"].isin(zip_set)
    s["flag_invalid_state"] = ~s["seller_state"].isin(VALID_STATES)
    return s


def clean_products(products, translation) -> pd.DataFrame:
    """R6, R7: English category with a column recording where it came from."""
    p = to_numeric(blank_to_null(products), [
        "product_name_lenght", "product_description_lenght", "product_photos_qty",
        "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"])
    table_map = dict(zip(translation["product_category_name"],
                         translation["product_category_name_english"]))
    cat = p["product_category_name"]
    from_table = cat.map(table_map)
    from_manual = cat.map(MANUAL_CATEGORY_MAP)
    p["category_source"] = np.select(
        [cat.isna(), from_table.notna(), from_manual.notna()],
        ["unknown", "translation_table", "manual"],
        default="untranslated")
    english = from_table.fillna(from_manual)
    p["product_category_english"] = english.where(cat.notna(), "unknown")
    return p


# ---------- validation ----------
def check_unique(name, df, cols):
    dup = int(df.duplicated(subset=cols).sum())
    return [] if dup == 0 else [f"{name}: {dup} duplicate rows on {cols}"]


def check_fk(name, child, ccol, parent, pcol):
    c = child[ccol].dropna()
    orphans = int((~c.isin(set(parent[pcol]))).sum())
    return [] if orphans == 0 else [f"{name}: {orphans} orphan rows"]


def validate(t: dict) -> list:
    problems = []
    problems += check_unique("customers", t["customers"], ["customer_id"])
    problems += check_unique("orders", t["orders"], ["order_id"])
    problems += check_unique("order_items", t["order_items"], ["order_id", "order_item_id"])
    problems += check_unique("payments", t["payments"], ["order_id", "payment_sequential"])
    problems += check_unique("reviews", t["reviews"], ["review_id", "order_id"])
    problems += check_unique("products", t["products"], ["product_id"])
    problems += check_unique("sellers", t["sellers"], ["seller_id"])
    problems += check_unique("geolocation_zip", t["geolocation_zip"], ["zip_code_prefix"])
    problems += check_unique("order_reviews", t["order_reviews"], ["order_id"])
    problems += check_unique("payments_by_order", t["payments_by_order"], ["order_id"])
    problems += check_unique("order_financials", t["order_financials"], ["order_id"])
    problems += check_fk("orders->customers", t["orders"], "customer_id", t["customers"], "customer_id")
    problems += check_fk("items->orders", t["order_items"], "order_id", t["orders"], "order_id")
    problems += check_fk("items->products", t["order_items"], "product_id", t["products"], "product_id")
    problems += check_fk("items->sellers", t["order_items"], "seller_id", t["sellers"], "seller_id")
    problems += check_fk("payments->orders", t["payments"], "order_id", t["orders"], "order_id")
    problems += check_fk("reviews->orders", t["reviews"], "order_id", t["orders"], "order_id")
    return problems


# ---------- pipeline ----------
def main() -> int:
    raw = {}
    for name, filename in FILES.items():
        path = RAW_DIR / filename
        if not path.exists():
            print(f"ERROR: missing raw file {path}")
            return 1
        raw[name] = pd.read_csv(path, dtype=str, keep_default_na=False)

    geo_zip = build_geolocation_zip(raw["geolocation"])
    zip_set = set(geo_zip["zip_code_prefix"])
    payments = clean_payments(raw["payments"])
    payments_by_order = build_payments_by_order(payments)
    reviews = clean_reviews(raw["reviews"])
    orders = clean_orders(raw["orders"], raw["order_items"], raw["payments"])
    items = clean_order_items(raw["order_items"])

    tables = {
        "customers": clean_customers(raw["customers"], zip_set),
        "orders": orders,
        "order_items": items,
        "payments": payments,
        "payments_by_order": payments_by_order,
        "order_financials": build_order_financials(orders, items, payments_by_order),
        "reviews": reviews,
        "order_reviews": build_order_reviews(reviews),
        "products": clean_products(raw["products"], blank_to_null(raw["translation"])),
        "sellers": clean_sellers(raw["sellers"], zip_set),
        "geolocation_zip": geo_zip,
        "category_translation": blank_to_null(raw["translation"]),
    }

    problems = validate(tables)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    source_of = {"customers": "customers", "orders": "orders", "order_items": "order_items",
                 "payments": "payments", "reviews": "reviews", "products": "products",
                 "sellers": "sellers", "geolocation_zip": "geolocation",
                 "category_translation": "translation",
                 "payments_by_order": "payments", "order_reviews": "reviews",
                 "order_financials": "orders"}
    summary = []
    for name, df in tables.items():
        df.to_csv(OUT_DIR / f"{name}_clean.csv", index=False)
        summary.append({"output_table": name, "source_table": source_of[name],
                        "source_rows": len(raw[source_of[name]]), "output_rows": len(df)})
    pd.DataFrame(summary).to_csv(REPORT_DIR / "cleaning_summary.csv", index=False)
    print(pd.DataFrame(summary).to_string(index=False))

    o = tables["orders"]
    print("\nFlag counts (orders):")
    for c in [c for c in o.columns if c.startswith("flag_")] + ["delivery_metric_eligible"]:
        print(f"  {c}: {int(o[c].sum())}")

    f = tables["order_financials"]
    print("\nOrder financials (R18):")
    print(f"  orders with items and payments, mismatch > 0.01: "
          f"{int(f['flag_payment_item_mismatch'].sum())}")
    print(f"  revenue-eligible orders: {int(f['is_revenue_eligible'].sum())}")
    print(f"  total revenue (sum of price, eligible orders): {f['revenue'].sum():.2f}")

    bad_zips = set(geo_zip.loc[geo_zip["flag_outside_brazil_box"], "zip_code_prefix"])
    print("\nGeolocation (R16):")
    print(f"  zips with coordinates set to missing: {len(bad_zips)}")
    print(f"  customers in those zips: "
          f"{int(tables['customers']['customer_zip_code_prefix'].isin(bad_zips).sum())}")
    print(f"  sellers in those zips: "
          f"{int(tables['sellers']['seller_zip_code_prefix'].isin(bad_zips).sum())}")

    p = tables["products"]
    print(f"\nProducts with zero weight (R19): {int(p['flag_zero_weight'].sum())}")
    print("Category source counts (products):")
    print(p["category_source"].value_counts().to_string())

    if problems:
        print("\nVALIDATION FAILED:")
        for msg in problems:
            print(" -", msg)
        return 1
    print("\nVALIDATION PASSED: keys unique, no orphan foreign keys.")
    print(f"Cleaned files written to: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())