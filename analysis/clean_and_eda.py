#Load and inspect
import pandas as pd

customers = pd.read_csv("data/customers.csv")
orders = pd.read_csv("data/orders.csv")
products = pd.read_csv("data/products.csv")
print("orders shape:", orders.shape)
print("customers shape:", customers.shape)
print("products shape:", products.shape)

# Standardize payment_method casing

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