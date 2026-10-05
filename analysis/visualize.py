
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
VIZ_DIR = BASE_DIR / "visualizations"

# --- Rebuild the minimum cleaned data needed ---
customers = pd.read_csv(DATA_DIR / "customers.csv")
products = pd.read_csv(DATA_DIR / "products.csv")
orders = pd.read_csv(DATA_DIR / "orders.csv")

orders['payment_method'] = orders['payment_method'].str.strip().str.upper()

duplicate_mask = orders.duplicated(
    subset=['customer_id', 'product_id', 'order_date', 'quantity',
            'discount_pct', 'payment_method', 'rating', 'returned'],
    keep='first'
)
orders_clean = orders[~duplicate_mask].copy()
orders_clean['discount_pct'] = orders_clean['discount_pct'].fillna(0)
orders_clean['rating'] = orders_clean['rating'].fillna(orders_clean['rating'].median())

merged = orders_clean.merge(products, on='product_id').merge(customers, on='customer_id')
merged['order_value'] = merged['quantity'] * merged['price'] * (1 - merged['discount_pct'] / 100)

Q1 = merged['quantity'].quantile(0.25)
Q3 = merged['quantity'].quantile(0.75)
IQR = Q3 - Q1
lower = Q1 - 1.5 * IQR
upper = Q3 + 1.5 * IQR
merged['is_outlier'] = (merged['quantity'] < lower) | (merged['quantity'] > upper)

merged['order_date'] = pd.to_datetime(merged['order_date'])
merged['order_month'] = merged['order_date'].dt.to_period('M')

VIZ_DIR.mkdir(exist_ok=True)

# --- Chart 1: return rate by payment method ---
return_rate = merged.groupby('payment_method')['returned'].mean() * 100
return_rate = return_rate.round(1).sort_values(ascending=False)

cod_rate = return_rate['COD']
card_rate = return_rate['CARD']
multiplier = round(cod_rate / card_rate, 1)
return_rate = return_rate.round(1).sort_values(ascending=False)
print("return_rate after sorting:")
print(return_rate)

ax1 = return_rate.plot(
    kind='bar', color='steelblue',
    title=f"COD Returns at {cod_rate}% — {multiplier}x Card",
    ylabel='Return rate (%)', xlabel='Payment method', ylim=(0, 100)
)
ax1.bar_label(ax1.containers[0], fmt='%.1f%%')
plt.tight_layout()
plt.savefig(VIZ_DIR / 'return_rate_by_payment.png', dpi=150)
plt.close()

# --- Chart 2: outlier-corrected monthly revenue trend ---
monthly_clean = merged[~merged['is_outlier']].groupby('order_month')['order_value'].sum()
peak_month = monthly_clean.idxmax()

ax2 = monthly_clean.plot(
    kind='line', marker='o', color='darkgreen',
    title=f"Monthly Revenue Trend — Peak Month: {peak_month}",
    ylabel='Revenue (₹)', xlabel='Month'
)
plt.tight_layout()
plt.savefig(VIZ_DIR / 'monthly_revenue_trend.png', dpi=150)
plt.close()

print("Saved return_rate_by_payment.png and monthly_revenue_trend.png to visualizations/")
# %%
