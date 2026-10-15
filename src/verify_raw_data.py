"""
verify_raw_data.py
Step 1 of Module 1: verify that the nine Olist CSV files exist, can be read,
match the published column names, and record a SHA-256 fingerprint of each file.

Run from the project root:
    python src/verify_raw_data.py
Never modifies the raw files.
"""
import hashlib
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
REPORT_DIR = PROJECT_ROOT / "reports" / "data_quality"

# Published Olist schema (note: "lenght" is the dataset's own spelling).
EXPECTED_COLUMNS = {
    "olist_customers_dataset.csv": [
        "customer_id", "customer_unique_id", "customer_zip_code_prefix",
        "customer_city", "customer_state"],
    "olist_geolocation_dataset.csv": [
        "geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng",
        "geolocation_city", "geolocation_state"],
    "olist_order_items_dataset.csv": [
        "order_id", "order_item_id", "product_id", "seller_id",
        "shipping_limit_date", "price", "freight_value"],
    "olist_order_payments_dataset.csv": [
        "order_id", "payment_sequential", "payment_type",
        "payment_installments", "payment_value"],
    "olist_order_reviews_dataset.csv": [
        "review_id", "order_id", "review_score", "review_comment_title",
        "review_comment_message", "review_creation_date",
        "review_answer_timestamp"],
    "olist_orders_dataset.csv": [
        "order_id", "customer_id", "order_status", "order_purchase_timestamp",
        "order_approved_at", "order_delivered_carrier_date",
        "order_delivered_customer_date", "order_estimated_delivery_date"],
    "olist_products_dataset.csv": [
        "product_id", "product_category_name", "product_name_lenght",
        "product_description_lenght", "product_photos_qty", "product_weight_g",
        "product_length_cm", "product_height_cm", "product_width_cm"],
    "olist_sellers_dataset.csv": [
        "seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
    "product_category_name_translation.csv": [
        "product_category_name", "product_category_name_english"],
}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not RAW_DIR.exists():
        print(f"ERROR: folder not found: {RAW_DIR}")
        return 1

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rows, problems = [], []

    for filename, expected_cols in EXPECTED_COLUMNS.items():
        path = RAW_DIR / filename
        if not path.exists():
            problems.append(f"MISSING FILE: {filename}")
            continue
        try:
            # dtype=str keeps values exactly as stored (e.g. zip codes with leading zeros).
            df = pd.read_csv(path, dtype=str, keep_default_na=False)
        except Exception as exc:
            problems.append(f"UNREADABLE: {filename} ({exc})")
            continue

        actual_cols = list(df.columns)
        missing = [c for c in expected_cols if c not in actual_cols]
        extra = [c for c in actual_cols if c not in expected_cols]
        if missing or extra:
            problems.append(
                f"SCHEMA DIFFERENCE in {filename}: missing={missing}, unexpected={extra}")

        rows.append({
            "file": filename,
            "size_bytes": path.stat().st_size,
            "row_count": len(df),
            "column_count": len(actual_cols),
            "columns": "|".join(actual_cols),
            "schema_matches_expected": not (missing or extra),
            "sha256": sha256_of(path),
        })

    manifest = pd.DataFrame(rows)
    out_path = REPORT_DIR / "raw_data_manifest.csv"
    manifest.to_csv(out_path, index=False)

    if not manifest.empty:
        print(manifest[["file", "row_count", "column_count",
                        "schema_matches_expected"]].to_string(index=False))
    print(f"\nManifest written to: {out_path}")

    if problems:
        print("\nPROBLEMS FOUND:")
        for p in problems:
            print(" -", p)
        return 1

    print("\nSUCCESS: all 9 files present, readable, and matching the expected schema.")
    return 0


if __name__ == "__main__":
    sys.exit(main())