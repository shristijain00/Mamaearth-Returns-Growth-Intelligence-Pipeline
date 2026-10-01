""" Order totals — COUNT(*), total revenue, and average order value, where revenue per row is quantity * price * (1 - discount_pct/100) """
"""and NULL discount is treated as 0% (COALESCE). Joins orders to products. — 2 marks Expected: total_orders = 180, total_revenue = 99860.20, avg_order_value = 554.78"""

SELECT COUNT(*) AS total_orders,
    SUM (o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0)/100.0) ) AS total_revenue,
    AVG(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0)/100.0)) AS avg_order_value
    
FROM orders o
JOIN products p ON o.product_id = p.product_id;

"""output : total_orders  total_revenue   avg_order_value
------------  -------------  -----------------
         180        99860.2  554.7788888888889"""

"""b) COUNT(*) vs COUNT(column) — one query showing COUNT(*), COUNT(rating),
 and the difference, on orders. — 2 marks Expected: (180, 165, 15) — 15 orders have no rating yet."""

SELECT 
  COUNT(*) AS total_orders,
  COUNT(rating) as orders_with_rating,
  COUNT(*) - COUNT(rating) AS orders_with_no_rating 
FROM orders;

"""output:total_orders  orders_with_rating  orders_with_no_ra...
------------  ------------------  --------------------
         180                 165                    15"""



 """ LEFT JOIN with a genuine zero-match row LEFT JOIN customers to orders, GROUP BY customer, HAVING COUNT(order_id) = 0, to find any customer with zero orders.
  Then write a second, independent query using NOT IN (SELECT DISTINCT customer_id FROM orders) that must return the same customer, confirming the LEFT JOIN result rather than trusting it blindly."""

SELECT c.customer_id ,c.name from customers c
   LEFT JOIN orders o on c.customer_id = o.customer_id
   GROUP BY c.customer_id
   HAVING COUNT(o.order_id) = 0;

SELECT customer_id, name FROM customers where customer_id NOT IN (SELECT DISTINCT customer_id FROM orders);

""" GROUP BY + HAVING — 
join orders to customers, group by city, compute total_orders, returned_orders, and return_rate_pct (rounded to 1 decimal),
 then filter with HAVING return_rate_pct > 20, ordered by return_rate_pct DESC. —
 Expected exactly 3 rows: Jaipur (19, 8, 42.1), Lucknow (49, 15, 30.6), Bangalore (33, 8, 24.2). (Mumbai at 17.9% and Delhi at 17.4% are correctly excluded.)"""


select 
  c.city,
  COUNT (o.order_id) as total_orders,
  SUM (o.returned) as returned_orders,
  ROUND( (SUM (o.returned )* 100.0/ count(o.order_id)) ,1) AS return_rate_pct

from orders o join customers c on o.customer_id = c.customer_id
group by c.city 
having return_rate_pct >20
order by return_rate_pct DESC;

"""output:   city     total_orders  returned_orders  return_rate_pct
---------  ------------  ---------------  ---------------
Jaipur               19                8             42.1
Lucknow              49               15             30.6
Bangalore            33                8             24.2
"""

 """e) Ranking with ORDER BY + LIMIT/OFFSET — 
 join orders, products, customers; group by customer;
  compute total_spend; order by total_spend DESC, customer_id ASC (the tie-break matters — state why in a one-line comment).
   Run it once with LIMIT 5 and once with LIMIT 3 OFFSET 2 to get ranks 3–5 without re-deriving the top 5. — 3 marks
  Expected top 5: C043 Reyansh 12920.00, C026 Isha 8371.60, C008 Meera 4564.60, C011 Arjun 4111.00, C042 Sanya 3785.00. The LIMIT 3 OFFSET 2 query must return exactly the last three of those five, in the same order.
"""
SELECT 
    c.customer_id,
    c.name,
    ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS total_spend
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN products p ON o.product_id = p.product_id
GROUP BY c.customer_id, c.name
ORDER BY total_spend DESC, c.customer_id ASC
LIMIT 3 OFFSET 2;

"""OUTPUT: customer_id  name   total_spend
-----------  -----  -----------
C008         Meera       4564.6
C011         Arjun       4111.0
C042         Sanya       3785.0"""

"""LIKE pattern match — customers whose name starts with 'A'. Expected: exactly 10 rows."""

SELECT * from customers where name LIKE 'A%'; 

output: customer_id   name     city     city_tier  signup_date  acquisition_source
-----------  ------  ---------  ---------  -----------  ------------------
C001         Aarav   Mumbai             1  2026-01-07   Organic
C003         Aditi   Mumbai             1  2026-06-23   Organic
C004         Ananya  Lucknow            2  2026-01-23   Organic
C011         Arjun   Bangalore          1  2026-03-13   Referral
C021         Aryan   Bangalore          1  2026-02-11   Ad
C030         Anika   Bangalore          1  2026-02-24   Organic
C031         Aditya  Jaipur             2  2026-06-14   Ad
C036         Aisha   Delhi              1  2026-05-11   Ad
C041         Ayaan   Lucknow            2  2026-01-03   Organic
C044         Aria    Bangalore          1  2026-04-22   Referral

""" DISTINCT — distinct acquisition_source values used across all customers.  Expected: exactly 4 values — Ad, Organic, Referral, Social."""

SELECT DISTINCT acquisition_source from customers;

"""output: acquisition_source
------------------
Organic
Referral
Ad
Social
sqlite>"""



""" ALTER TABLE + UPDATE with CASE — add a loyalty_tier VARCHAR(10) column to customers, then a single UPDATE ... SET loyalty_tier = CASE WHEN city_tier = 1 THEN 'Gold'
 ELSE 'Silver' END (no WHERE clause — every row gets a value). 
 Expected: SELECT loyalty_tier, COUNT(*) FROM customers GROUP BY loyalty_tier;
 → Gold, 28 and Silver, 17."""
  
  ALTER TABLE customers ADD column loyalty_tier VARCHAR(10);
 
  UPDATE customers 
  SET loyalty_tier = CASE 
    WHEN city_tier = 1 then 'Gold'
    ELSE 'Silver'
  END;

""" SELECT loyalty_tier, COUNT(*) FROM customers GROUP BY loyalty_tier;

output: loyalty_tier  COUNT(*)
------------  --------
Gold                28
Silver              17"""