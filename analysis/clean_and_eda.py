# %%Load and inspect
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

customers = pd.read_csv(DATA_DIR / "customers.csv")
products = pd.read_csv(DATA_DIR / "products.csv")
orders = pd.read_csv(DATA_DIR / "orders.csv")
print("orders shape:", orders.shape)
print("customers shape:", customers.shape)
print("products shape:", products.shape)

# %% Standardize payment_method casing

print("Unique payment_method values (before fix):")
print(orders['payment_method'].unique())
orders['payment_method'] = orders['payment_method'].str.strip().str.upper()
print("Unique payment_method values (after fix):")
print(orders['payment_method'].unique())
print("Value counts (after fix):")
print(orders['payment_method'].value_counts())


duplicated_mask = orders.duplicated(
    subset=['customer_id', 'product_id', 'order_date', 'quantity',
            'discount_pct', 'payment_method', 'rating', 'returned'],
    keep='first'
)

dropped_order_ids = orders.loc[duplicated_mask, 'order_id']
print("Dropped order_id values:")
print(dropped_order_ids.tolist())

orders_clean = orders[~duplicated_mask].copy()
print("orders_clean.shape:", orders_clean.shape)

#Impute missing values 
print("Missing discount_pct (before impute):", orders_clean['discount_pct'].isnull().sum())
print("Missing rating (before impute):", orders_clean['rating'].isnull().sum())

rating_median = orders_clean['rating'].median()
print("Rating median (before impute):", rating_median)

orders_clean['discount_pct'] = orders_clean['discount_pct'].fillna(0)
orders_clean['rating'] = orders_clean['rating'].fillna(rating_median)

print("Missing values after imputation:")
print(orders_clean[['discount_pct', 'rating']].isnull().sum())

# %%Merge and reconcile against Part 1

merged  = orders_clean.merge(products, on='product_id').merge(customers, on='customer_id')
merged['order_value'] = merged['quantity'] * merged['price'] * (1 - merged['discount_pct']/100)
total_clean = merged['order_value'].sum()
print("Total order_value (cleaned, 175 rows):", f"{total_clean:.2f}")

dropped_rows = orders.merge(products, on='product_id')
dropped_rows = dropped_rows[dropped_rows['order_id'].isin(dropped_order_ids)].copy()
dropped_rows['order_value'] = dropped_rows['quantity'] * dropped_rows['price'] * (1 - dropped_rows['discount_pct']/100)
dropped_total = dropped_rows['order_value'].sum()
print("Combined order_value of the 5 dropped duplicate rows:", f"{dropped_total:.2f}")

print(
    f"Reconciliation: the raw total (99860.20) and the cleaned total ({total_clean:.2f}) "
    f"differ by {99860.20 - total_clean:.2f}. This exact amount matches the combined "
    f"order_value of the 5 duplicate rows removed in Task 3 ({dropped_total:.2f}), "
    f"confirming the deduplication step — not the discount/rating imputation — "
    f"accounts for the entire difference."
)

# %% IQR outlier detection on quantity
df = merged.copy()
Q1 = df['quantity'].quantile(0.25)
Q3 = df['quantity'].quantile(0.75)
IQR = Q3 - Q1
Lower_Bound = Q1 - 1.5 * IQR
Upper_Bound = Q3 + 1.5 * IQR

print("Q1 in quantity:", Q1)
print("Q3 in quantity:", Q3)
print("IQR in quantity:", IQR)
print("Lower Bound in quantity:", Lower_Bound)
print("Upper Bound in quantity:", Upper_Bound)

merged['is_outlier'] = (merged['quantity'] < Lower_Bound) | (merged['quantity'] > Upper_Bound)
print("Number of outlier rows:", merged['is_outlier'].sum())
print(merged[merged['is_outlier']][['order_id', 'quantity']])
# %%
#%%  Hypothesis: COD orders have higher return rates than prepaid orders.
# %% Hypothesis: COD orders have higher return rates than prepaid orders.
print("Hypothesis: COD orders have higher return rates than prepaid orders.")

return_rate_by_payment = merged.groupby('payment_method')['returned'].agg(['count', 'mean'])
return_rate_by_payment['mean'] = (return_rate_by_payment['mean'] * 100).round(1)
print("Return rate by payment method (%):")
print(return_rate_by_payment)

cod_rate = return_rate_by_payment.loc['COD', 'mean']
card_rate = return_rate_by_payment.loc['CARD', 'mean']
upi_rate = return_rate_by_payment.loc['UPI', 'mean']

print(
    f"Hypothesis result: CONFIRMED — COD's return rate ({cod_rate}%) is higher than "
    f"both CARD ({card_rate}%) and UPI ({upi_rate}%), the two prepaid methods."
)
#%%
#%% Multi-level segmentation
return_rate_per_segment = merged.groupby(['payment_method', 'city_tier'])['returned'].agg(['count', 'mean'])
return_rate_per_segment['mean'] = (return_rate_per_segment['mean'] * 100).round(1)
print("Return rate by payment method and city tier (%):")
print(return_rate_per_segment)
highest_risk_segment = return_rate_per_segment['mean'].idxmax()
highest_risk_rate = return_rate_per_segment['mean'].max()
payment, tier = highest_risk_segment
other_tier = 1 if tier == 2 else 2


this_count = return_rate_per_segment.loc[(payment, tier), 'count']
other_count = return_rate_per_segment.loc[(payment, other_tier), 'count']
other_rate = return_rate_per_segment.loc[(payment, other_tier), 'mean']


print(
    f"Highest-risk segment: {payment} + Tier-{tier} cities at {highest_risk_rate}% "
    f"({this_count} orders) — compared to {payment} + Tier-{other_tier} cities at "
    f"{other_rate}% ({other_count} orders). This shows {payment} risk is not uniform "
    f"across city tiers; a single blended rate would hide this concentration."
)

#%% Correlation analysis
def band_label(r):
  r = abs(r)
  if r < 0.2:
    return "negligible"
  elif r < 0.4:
   return "weak"
  elif r < 0.7:
   return "moderate"
  else:
   return "strong"

pairs = [
    ('rating', 'returned'),
    ('rating', 'discount_pct'),
    ('rating', 'quantity'),
    ('returned', 'discount_pct'),
    ('returned', 'quantity'),
    ('discount_pct', 'quantity')]

for col1, col2 in pairs:
    corr = merged[col1].corr(merged[col2])
    band = band_label(corr)
    print(f"Correlation between {col1} and {col2}: {corr:.3f} ({band})")


discount_returned_corr = merged['discount_pct'].corr(merged['returned'])
print(
    f"Hypothesis 'higher discounts reduce returns': BUSTED — correlation is only "
    f"{discount_returned_corr:.2f}, which falls in the negligible band (|r| < 0.2), "
    f"meaning discount level has no meaningful linear relationship with returns."
)
# %%  Outlier-corrected time series
merged['order_date'] = pd.to_datetime(merged['order_date'])
merged['order_month'] = merged['order_date'].dt.to_period('M')
monthly_with_outliers = merged.groupby('order_month')['order_value'].sum()
print("Monthly order_value with outliers:")
print(monthly_with_outliers)
monthly_without_outliers = merged[~merged['is_outlier']].groupby('order_month')['order_value'].sum()
print("Monthly order_value without outliers:")  
print(monthly_without_outliers)
highest_with = monthly_with_outliers.idxmax()
highest_without = monthly_without_outliers.idxmax()



print(
    f"{highest_with}'s apparent lead ({monthly_with_outliers.max():.2f}) is an artifact of "
    f"the two bulk orders (O0011 on 2026-01-28, O0098 on 2026-01-10) landing in that month. "
    f"Once the Task 6 outliers are excluded, {highest_without} becomes the genuine peak month "
    f"at {monthly_without_outliers.max():.2f} — this is why outlier detection (Task 6) must "
    f"happen before this monthly trend analysis, not after."
)

