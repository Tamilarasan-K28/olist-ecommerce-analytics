"""
ml_final.py: FINAL evaluation. Commit this file BEFORE running it.
Pre-declared plan (fixed from validation results, before the test split is looked at):
  primary model     : hgb_time (best validation PR-AUC)
  sensitivity model : hgb_time_no_month (reported, NOT used to choose)
  comparators       : never_late, rule_cross_state, logreg_base
  operating points  : (a) validation best-F1 threshold, (b) flag the top 10% of test scores
Fit on TRAIN; threshold chosen on VALIDATION; TEST evaluated once.
Run: python -m src.ml_final   (refuses to rerun; --force only with a documented reason)
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import (average_precision_score, confusion_matrix,
                             precision_recall_curve, roc_auc_score)

from src.db import get_engine
from src.ml_baselines import CAT, LOG_COLS, NUM
from src.ml_experiments import SQL_ALL, SQL_EXTRA, TIME, hgb, logreg, prior_rate

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "ml_dataset.csv"
RES_JSON = ROOT / "reports" / "ml_test_results.json"
RES_CSV = ROOT / "reports" / "ml_test_results.csv"
CARD = ROOT / "docs" / "ml_model_card.md"
MODEL = ROOT / "models" / "late_delivery_hgb_time.joblib"
TOP_FRAC = 0.10


def build_frame():
    eng = get_engine()
    df = pd.read_csv(DATA, parse_dates=["purchase_ts"])
    df = df.merge(pd.read_sql_query(SQL_EXTRA, eng, parse_dates=["delivered_ts"]),
                  on="order_id", how="left")
    assert len(df) == 96470 and df["delivered_ts"].notna().all()
    df = df.sort_values("purchase_ts").reset_index(drop=True)
    df["all"] = 1
    prior = float(df.loc[df["split"] == "train", "is_late"].mean())
    df["platform_late_14d"], df["platform_n_14d"] = prior_rate(df, "all", 14, 50, prior)
    df["state_late_30d"], df["state_n_30d"] = prior_rate(df, "customer_state", 30, 30, prior)
    df["seller_late_prior"], df["seller_n_prior"] = prior_rate(df, "seller_id", None, 20, prior)
    ts_all = np.sort(pd.to_datetime(pd.read_sql_query(SQL_ALL, eng)["ts"]).values)
    p = df["purchase_ts"].values
    df["orders_last_7d"] = (np.searchsorted(ts_all, p, side="left")
                            - np.searchsorted(ts_all, p - np.timedelta64(7, "D"), side="left"))
    for c in LOG_COLS:
        df[c] = np.log1p(df[c])
    return df, prior


def op_metrics(y, pred):
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    prec, rec = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    return {"flagged": int(tp + fp), "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1": round(float(2 * prec * rec / max(prec + rec, 1e-12)), 4),
            "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn)}


def val_threshold(y, s):
    p, r, t = precision_recall_curve(y, s)
    f1 = 2 * p[:-1] * r[:-1] / np.maximum(p[:-1] + r[:-1], 1e-12)
    return float(t[f1.argmax()])


def boot(y, s, reps=200, seed=0):
    rng, n, r, a = np.random.default_rng(seed), len(y), [], []
    for _ in range(reps):
        i = rng.integers(0, n, n)
        if y[i].min() == y[i].max():
            continue
        r.append(roc_auc_score(y[i], s[i]))
        a.append(average_precision_score(y[i], s[i]))
    return {"roc_auc_95ci": np.percentile(r, [2.5, 97.5]).round(4).tolist(),
            "pr_auc_95ci": np.percentile(a, [2.5, 97.5]).round(4).tolist()}


def md_table(d):
    cols = list(d.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(str(r[c]) for c in cols) + " |" for _, r in d.iterrows()]
    return "\n".join(out)


def main():
    if RES_JSON.exists() and "--force" not in sys.argv:
        print("Test results already exist. The test split is used once. "
              "Use --force only with a documented reason.")
        return 1
    print("EVALUATING THE TEST SPLIT NOW (once).")
    df, prior = build_frame()
    cats = {c: sorted(df.loc[df["split"] == "train", c].dropna().unique()) for c in CAT}
    dh = df.copy()
    for c in CAT:
        dh[c] = pd.Categorical(dh[c], categories=cats[c])      # unseen values become missing
    te = df[df["split"] == "test"]
    yt = te["is_late"].to_numpy()
    print(f"test orders {len(te):,} | late rate {yt.mean():.4f}")

    base = NUM + CAT
    time_all = base + TIME
    specs = [("logreg_base", logreg(NUM), df, base),
             ("hgb_time", hgb(), dh, time_all),
             ("hgb_time_no_month", hgb(), dh, [c for c in time_all if c != "purchase_month"])]
    z = np.zeros(len(te), dtype=int)
    cross = (1 - te["same_state"]).to_numpy()
    rows = [{"model": "never_late", "operating_point": "always_on_time", "roc_auc": 0.5,
             "pr_auc": round(float(yt.mean()), 4), **op_metrics(yt, z)},
            {"model": "rule_cross_state", "operating_point": "cross_state",
             "roc_auc": round(float(roc_auc_score(yt, cross)), 4),
             "pr_auc": round(float(average_precision_score(yt, cross)), 4), **op_metrics(yt, cross)}]
    kept = {}
    for name, model, frame, feats in specs:
        tr = frame[frame["split"] == "train"]
        v = frame[frame["split"] == "validation"]
        t = frame[frame["split"] == "test"]
        model.fit(tr[feats], tr["is_late"])
        sv, st = model.predict_proba(v[feats])[:, 1], model.predict_proba(t[feats])[:, 1]
        thr = val_threshold(v["is_late"].to_numpy(), sv)
        auc = round(float(roc_auc_score(yt, st)), 4)
        ap = round(float(average_precision_score(yt, st)), 4)
        rows.append({"model": name, "operating_point": f"val_best_f1_thr_{thr:.3f}",
                     "roc_auc": auc, "pr_auc": ap, **op_metrics(yt, (st >= thr).astype(int))})
        top = np.zeros(len(st), dtype=int)
        top[np.argsort(-st)[:int(TOP_FRAC * len(st))]] = 1
        rows.append({"model": name, "operating_point": "top_10pct_by_score",
                     "roc_auc": auc, "pr_auc": ap, **op_metrics(yt, top)})
        kept[name] = (st, thr, model, feats, top)
    res = pd.DataFrame(rows)
    res["lift"] = (res["precision"] / yt.mean()).round(2)
    print(res.to_string(index=False))

    st, thr, model, feats, top = kept["hgb_time"]
    ci = {n: boot(yt, kept[n][0]) for n in ("hgb_time", "logreg_base")}
    print("bootstrap 95% intervals (orders resampled; approximate):", ci)
    month = te["purchase_ts"].dt.to_period("M").astype(str).to_numpy()
    mrows = []
    for m in sorted(set(month)):
        k = month == m
        mrows.append({"month": m, "orders": int(k.sum()), "late_rate": round(float(yt[k].mean()), 4),
                      "mean_score": round(float(st[k].mean()), 4),
                      "roc_auc": round(float(roc_auc_score(yt[k], st[k])), 4)})
    monthly = pd.DataFrame(mrows)
    print("\nprimary model by month:\n", monthly.to_string(index=False))
    miss = te[(yt == 1) & (top == 0)]["customer_state"].value_counts().head(5)
    print("\nlate orders missed by the top-10% rule, by customer state (top 5):\n", miss.to_string())

    MODEL.parent.mkdir(exist_ok=True)
    joblib.dump({"model": model, "features": feats, "categories": cats, "prior": prior,
                 "threshold": thr, "sklearn": sklearn.__version__}, MODEL)
    res.to_csv(RES_CSV, index=False)
    RES_JSON.write_text(json.dumps({"run_at": datetime.now().isoformat(timespec="seconds"),
                                    "test_orders": int(len(te)), "test_late_rate": float(yt.mean()),
                                    "ci": ci, "results": res.to_dict("records"),
                                    "monthly": monthly.to_dict("records")}, indent=1, default=str),
                        encoding="utf-8")
    CARD.write_text(f"""# Model card: late-delivery risk (primary model hgb_time)

Generated by src/ml_final.py from reports/ml_test_results.json. Test split used once.

## Task
Predict, at purchase time, whether an order will arrive after its estimated delivery date.

## Data and split
Olist delivery-eligible orders (96,470). Train 2017-01 to 2018-02, validation 2018-03 to 2018-05 (threshold), test 2018-06 to 2018-08. Test: {len(te):,} orders, late rate {yt.mean():.4f}.

## Model
HistGradientBoostingClassifier on order features known at purchase plus time-aware rates (platform, state, seller) computed only from earlier deliveries. Plan fixed before the test run (see the header of src/ml_final.py).

## Test results
{md_table(res)}

Bootstrap 95% intervals (approximate): {json.dumps(ci)}

## Primary model by month (test)
{md_table(monthly)}

## Limitations
- Late rates vary from month to month (1.36% to 21.36%); the model ranks orders but its average score does not follow the monthly level.
- The validation threshold was chosen on a period with a different late rate than the test period, so precision at that threshold shifts.
- One time split, one marketplace, about two years; no claim of generalisation.
- Feature importance describes association in this data, not cause.
- Delivered orders only; orders still undelivered at the end of the data are absent.
- Payment details are assumed known at purchase (no payment timestamps in the data).
""", encoding="utf-8")
    print("\nWrote results, model card and model.")
    return 0


if __name__ == "__main__":
    sys.exit(main())