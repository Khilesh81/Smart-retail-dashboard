-- ============================================================
-- Retail Store Analytics System — Database Schema
-- PostgreSQL
-- ============================================================

-- Categories
CREATE TABLE IF NOT EXISTS categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Products
CREATE TABLE IF NOT EXISTS products (
    id              SERIAL PRIMARY KEY,
    category_id     INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    name            VARCHAR(255) NOT NULL,
    sku             VARCHAR(100) UNIQUE NOT NULL,
    purchase_price  DECIMAL(10,2) NOT NULL CHECK (purchase_price >= 0),
    selling_price   DECIMAL(10,2) NOT NULL CHECK (selling_price >= 0),
    stock_quantity  INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    min_stock_level INTEGER NOT NULL DEFAULT 10,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Customers
CREATE TABLE IF NOT EXISTS customers (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(255) NOT NULL,
    phone      VARCHAR(20),
    email      VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert a default walk-in customer
INSERT INTO customers (name, phone, email)
SELECT 'Walk-in Customer', '0000000000', 'walkin@store.local'
WHERE NOT EXISTS (SELECT 1 FROM customers WHERE email = 'walkin@store.local');

-- Sales (Bills)
CREATE TABLE IF NOT EXISTS sales (
    id              SERIAL PRIMARY KEY,
    customer_id     INTEGER REFERENCES customers(id) ON DELETE SET NULL,
    sale_date       TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    total_amount    DECIMAL(10,2) NOT NULL DEFAULT 0,
    discount        DECIMAL(10,2) NOT NULL DEFAULT 0,
    net_amount      DECIMAL(10,2) NOT NULL DEFAULT 0,
    payment_method  VARCHAR(50) DEFAULT 'Cash',
    status          VARCHAR(50) DEFAULT 'Completed',
    notes           TEXT
);

-- Sale Items (Line Items)
CREATE TABLE IF NOT EXISTS sale_items (
    id                      SERIAL PRIMARY KEY,
    sale_id                 INTEGER REFERENCES sales(id) ON DELETE CASCADE,
    product_id              INTEGER REFERENCES products(id) ON DELETE RESTRICT,
    quantity                INTEGER NOT NULL CHECK (quantity > 0),
    unit_price              DECIMAL(10,2) NOT NULL,
    purchase_price_at_sale  DECIMAL(10,2) NOT NULL,
    total_price             DECIMAL(10,2) NOT NULL
);

-- Payments
CREATE TABLE IF NOT EXISTS payments (
    id           SERIAL PRIMARY KEY,
    sale_id      INTEGER REFERENCES sales(id) ON DELETE CASCADE,
    payment_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    amount       DECIMAL(10,2) NOT NULL,
    method       VARCHAR(50) DEFAULT 'Cash'
);

-- Inventory Movements
CREATE TABLE IF NOT EXISTS inventory_movements (
    id              SERIAL PRIMARY KEY,
    product_id      INTEGER REFERENCES products(id) ON DELETE CASCADE,
    movement_type   VARCHAR(20) NOT NULL CHECK (movement_type IN ('IN', 'OUT', 'ADJUSTMENT')),
    quantity        INTEGER NOT NULL,
    movement_date   TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reference_id    INTEGER,
    notes           TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_products_category   ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_sku        ON products(sku);
CREATE INDEX IF NOT EXISTS idx_sales_date          ON sales(sale_date);
CREATE INDEX IF NOT EXISTS idx_sales_customer      ON sales(customer_id);
CREATE INDEX IF NOT EXISTS idx_sale_items_sale     ON sale_items(sale_id);
CREATE INDEX IF NOT EXISTS idx_sale_items_product  ON sale_items(product_id);
CREATE INDEX IF NOT EXISTS idx_inv_mov_product     ON inventory_movements(product_id);
