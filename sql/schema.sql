DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS products;


PRAGMA foreign_keys = ON;
Create table customers(
    customer_id varchar(10)  PRIMARY KEY NOT NULL,
    name VARCHAR(50) NOT NULL,
    city varchar(50) NOT NULL,
    city_tier INT NOT NULL,
    signup_date DATE NOT NULL,
    acquisition_source VARCHAR(20) NOT NULL
    );


Create table products(
    product_id VARCHAR(10) PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
     category VARCHAR(30) NOT NULL, 
     price DECIMAL(10,2) NOT NULL
);

Create table orders(
    order_id VARCHAR(10) PRIMARY KEY,
    customer_id VARCHAR(10) NOT NULL,
    product_id VARCHAR(10) NOT NULL,
    order_date DATE NOT NULL, 
    quantity INT NOT NULL CHECK(quantity >0), 
    discount_pct INT CHECK (discount_pct BETWEEN 0 AND 100), 
    payment_method VARCHAR(10) NOT NULL, 
    rating INT CHECK (rating BETWEEN 1 AND 5), 
    returned INT NOT NULL DEFAULT 0, 
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id), 
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);