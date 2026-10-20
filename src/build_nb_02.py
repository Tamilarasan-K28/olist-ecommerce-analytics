"""build_nb_02.py: writes notebooks/02_order_trends.ipynb (run once)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": text.splitlines(True)}


cells = [
    md("# 02 Order trends\n\nMonthly orders and revenue. Trend window: 2017-01 to 2018-08 "
       "(assumption A1, see docs/database_schema.md). Months outside it are shown separately."),
    code("import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path.cwd().parent))\n\n"
         "import pandas as pd\nimport matplotlib.pyplot as plt\n"
         "from src.db import read_table, TREND_START, TREND_END\n\n"
         "orders = read_table('fact_orders')\n"
         "orders['order_purchase_timestamp'] = pd.to_datetime(orders['order_purchase_timestamp'])\n"
         "orders['month'] = orders['order_purchase_timestamp'].dt.to_period('M').dt.to_timestamp()\n"
         "orders['revenue'] = orders['revenue'].astype(float)\n"
         "print(len(orders), 'orders loaded')"),
    code("monthly = (orders.groupby('month')\n"
         "          .agg(all_orders=('order_id', 'size'),\n"
         "               eligible_orders=('is_revenue_eligible', 'sum'),\n"
         "               revenue=('revenue', 'sum'))\n"
         "          .reset_index())\n"
         "monthly['in_window'] = monthly['month'].between(TREND_START, TREND_END)\n"
         "monthly"),
    code("win = monthly[monthly['in_window']]\n"
         "print('months in window:', len(win))\n"
         "print('orders in window:', int(win['all_orders'].sum()), 'of', int(monthly['all_orders'].sum()))\n"
         "print('revenue in window:', round(win['revenue'].sum(), 2), 'of', round(monthly['revenue'].sum(), 2))"),
    code("fig, ax = plt.subplots(1, 2, figsize=(13, 4))\n"
         "ax[0].plot(win['month'], win['all_orders'], marker='o')\n"
         "ax[0].set_title('Orders per month (2017-01 to 2018-08)')\n"
         "ax[0].set_ylabel('orders')\n"
         "ax[1].plot(win['month'], win['revenue'], marker='o', color='tab:green')\n"
         "ax[1].set_title('Revenue per month (sum of item price)')\n"
         "ax[1].set_ylabel('revenue (currency not stated in dataset)')\n"
         "for a in ax:\n    a.tick_params(axis='x', rotation=45)\n"
         "plt.tight_layout()\n"
         "out = Path.cwd().parent / 'reports' / 'figures' / 'monthly_orders_revenue.png'\n"
         "out.parent.mkdir(parents=True, exist_ok=True)\n"
         "fig.savefig(out, dpi=150)\n"
         "plt.show()"),
    md("## Reading the chart\n\nWrite your own observations here after viewing the chart. "
       "Describe what you see (levels, the November 2017 peak if present, early-2017 ramp-up) "
       "and avoid causal claims the data cannot support."),
]
nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
      "nbformat": 4, "nbformat_minor": 5}
out = ROOT / "notebooks" / "02_order_trends.ipynb"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(nb, indent=1), encoding="utf-8")
print("Wrote", out)