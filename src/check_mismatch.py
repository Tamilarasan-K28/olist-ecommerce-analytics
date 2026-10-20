# save as src\check_mismatch.py, run: python src\check_mismatch.py
import pandas as pd
from pathlib import Path

root = Path(__file__).resolve().parents[1]
f = pd.read_csv(root / "data" / "processed" / "order_financials_clean.csv")
both = f["items_price_total"].notna() & f["payment_total"].notna()
f = f[both].copy()
raw_diff = (f["payment_total"] - f["items_price_total"] - f["items_freight_total"]).abs()
print("orders with both:", len(f))
for t in (0.001, 0.005, 0.01, 0.02, 1, 10):
    print(f"raw |diff| > {t}: {int((raw_diff > t).sum())}")
print("rounded-diff flag count:", int(f["flag_payment_item_mismatch"].sum()))
print("\nstatus of flagged orders:")
print(f.loc[f["flag_payment_item_mismatch"], "order_status"].value_counts().to_string())