"""
backend.py — All CRUD, analytics, billing, and CSV logic
"""
import io
import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from database import (
    get_connection, release_connection,
    DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME,
)

# ── SQLAlchemy engine (for Pandas read_sql) ───────────────────────────────────
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        url = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def _df(query: str, params: dict | None = None) -> pd.DataFrame:
    """Run a SELECT and return a DataFrame."""
    try:
        with get_engine().connect() as con:
            return pd.read_sql(text(query), con, params=params or {})
    except Exception:
        return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORIES
# ══════════════════════════════════════════════════════════════════════════════

def get_all_categories() -> pd.DataFrame:
    return _df("SELECT * FROM categories ORDER BY name")


def add_category(name: str, description: str = "") -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO categories (name, description) VALUES (%s, %s)",
                (name.strip(), description.strip()),
            )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        release_connection(conn)


def delete_category(category_id: int) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM categories WHERE id = %s", (category_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        release_connection(conn)


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCTS
# ══════════════════════════════════════════════════════════════════════════════

def get_all_products() -> pd.DataFrame:
    query = """
        SELECT p.id, c.name AS category, p.name, p.sku,
               p.purchase_price, p.selling_price, p.stock_quantity,
               p.min_stock_level, p.is_active, p.created_at
        FROM   products p
        LEFT JOIN categories c ON p.category_id = c.id
        ORDER BY p.name
    """
    return _df(query)


def get_product_by_id(product_id: int) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
            row = cur.fetchone()
            if row:
                cols = [d[0] for d in cur.description]
                return dict(zip(cols, row))
        return None
    finally:
        release_connection(conn)


def add_product(
    category_id, name, sku, purchase_price, selling_price,
    stock_quantity, min_stock_level
) -> tuple[bool, str]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO products
                    (category_id, name, sku, purchase_price, selling_price,
                     stock_quantity, min_stock_level)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                (category_id, name.strip(), sku.strip().upper(),
                 purchase_price, selling_price, stock_quantity, min_stock_level),
            )
            if stock_quantity > 0:
                cur.execute(
                    "SELECT id FROM products WHERE sku = %s", (sku.strip().upper(),)
                )
                pid = cur.fetchone()[0]
                cur.execute(
                    """INSERT INTO inventory_movements
                       (product_id, movement_type, quantity, notes)
                       VALUES (%s,'IN',%s,'Initial stock')""",
                    (pid, stock_quantity),
                )
        conn.commit()
        return True, "Product added."
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        release_connection(conn)


def update_product(
    product_id, category_id, name, sku, purchase_price,
    selling_price, min_stock_level, is_active
) -> tuple[bool, str]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE products SET
                    category_id=%s, name=%s, sku=%s, purchase_price=%s,
                    selling_price=%s, min_stock_level=%s, is_active=%s,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=%s
                """,
                (category_id, name, sku.upper(), purchase_price,
                 selling_price, min_stock_level, is_active, product_id),
            )
        conn.commit()
        return True, "Product updated."
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        release_connection(conn)


def restock_product(product_id: int, qty: int, notes: str = "") -> tuple[bool, str]:
    if qty <= 0:
        return False, "Quantity must be positive."
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE products SET stock_quantity = stock_quantity + %s, "
                "updated_at=CURRENT_TIMESTAMP WHERE id=%s",
                (qty, product_id),
            )
            cur.execute(
                "INSERT INTO inventory_movements "
                "(product_id, movement_type, quantity, notes) VALUES (%s,'IN',%s,%s)",
                (product_id, qty, notes or f"Restock +{qty}"),
            )
        conn.commit()
        return True, f"Restocked {qty} units."
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        release_connection(conn)


def delete_product(product_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM products WHERE id=%s", (product_id,))
        conn.commit()
        return True, "Product deleted."
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        release_connection(conn)


# ══════════════════════════════════════════════════════════════════════════════
# CUSTOMERS
# ══════════════════════════════════════════════════════════════════════════════

def get_all_customers() -> pd.DataFrame:
    return _df("SELECT * FROM customers ORDER BY name")


def add_customer(name: str, phone: str = "", email: str = "") -> tuple[int | None, str]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO customers (name, phone, email) VALUES (%s,%s,%s) RETURNING id",
                (name.strip(), phone.strip(), email.strip()),
            )
            cid = cur.fetchone()[0]
        conn.commit()
        return cid, "Customer added."
    except Exception as e:
        conn.rollback()
        return None, str(e)
    finally:
        release_connection(conn)


# ══════════════════════════════════════════════════════════════════════════════
# BILLING — process_sale (atomic)
# ══════════════════════════════════════════════════════════════════════════════

def process_sale(
    customer_id: int,
    cart_items: list[dict],
    discount: float = 0.0,
    payment_method: str = "Cash",
    notes: str = "",
) -> tuple[bool, int | str]:
    """
    Atomically process a sale.
    cart_items: [{'product_id': int, 'quantity': int,
                  'unit_price': float, 'purchase_price': float}]
    Returns (True, sale_id) or (False, error_message).
    """
    if not cart_items:
        return False, "Cart is empty."

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            total_amount = sum(i["unit_price"] * i["quantity"] for i in cart_items)
            net_amount   = max(0.0, total_amount - discount)

            # 1 — create sale record
            cur.execute(
                """INSERT INTO sales
                   (customer_id, total_amount, discount, net_amount, payment_method, notes)
                   VALUES (%s,%s,%s,%s,%s,%s) RETURNING id""",
                (customer_id, total_amount, discount, net_amount, payment_method, notes),
            )
            sale_id = cur.fetchone()[0]

            for item in cart_items:
                pid   = item["product_id"]
                qty   = item["quantity"]
                price = item["unit_price"]
                cost  = item["purchase_price"]

                # 2 — deduct stock (DB CHECK constraint prevents negatives)
                cur.execute(
                    "UPDATE products SET stock_quantity = stock_quantity - %s,"
                    " updated_at=CURRENT_TIMESTAMP WHERE id=%s RETURNING stock_quantity",
                    (qty, pid),
                )
                row = cur.fetchone()
                if row is None:
                    raise ValueError(f"Product ID {pid} not found.")
                if row[0] < 0:
                    raise ValueError(f"Insufficient stock for product ID {pid}.")

                # 3 — sale item
                cur.execute(
                    """INSERT INTO sale_items
                       (sale_id, product_id, quantity, unit_price,
                        purchase_price_at_sale, total_price)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (sale_id, pid, qty, price, cost, price * qty),
                )

                # 4 — inventory movement
                cur.execute(
                    """INSERT INTO inventory_movements
                       (product_id, movement_type, quantity, reference_id, notes)
                       VALUES (%s,'OUT',%s,%s,%s)""",
                    (pid, -qty, sale_id, f"Sale #{sale_id}"),
                )

            # 5 — payment record
            cur.execute(
                "INSERT INTO payments (sale_id, amount, method) VALUES (%s,%s,%s)",
                (sale_id, net_amount, payment_method),
            )

        conn.commit()
        return True, sale_id

    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        release_connection(conn)


def get_sale_receipt(sale_id: int) -> dict:
    """Fetch full receipt data for a sale."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT s.*, c.name AS customer_name, c.phone
                   FROM sales s LEFT JOIN customers c ON s.customer_id=c.id
                   WHERE s.id=%s""",
                (sale_id,),
            )
            cols = [d[0] for d in cur.description]
            sale_row = cur.fetchone()
            if not sale_row:
                return {}
            sale = dict(zip(cols, sale_row))

            cur.execute(
                """SELECT si.*, p.name AS product_name, p.sku
                   FROM sale_items si JOIN products p ON si.product_id=p.id
                   WHERE si.sale_id=%s""",
                (sale_id,),
            )
            cols2 = [d[0] for d in cur.description]
            sale["items"] = [dict(zip(cols2, r)) for r in cur.fetchall()]
        return sale
    finally:
        release_connection(conn)


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS & REPORTS
# ══════════════════════════════════════════════════════════════════════════════

def get_sales_report(
    start_date: datetime.date | None = None,
    end_date:   datetime.date | None = None,
) -> pd.DataFrame:
    where  = "WHERE 1=1"
    params: dict = {}
    if start_date:
        where += " AND DATE(s.sale_date) >= :start_date"
        params["start_date"] = start_date
    if end_date:
        where += " AND DATE(s.sale_date) <= :end_date"
        params["end_date"] = end_date

    query = f"""
        SELECT s.id AS sale_id,
               s.sale_date,
               COALESCE(c.name,'Walk-in') AS customer,
               s.total_amount, s.discount, s.net_amount,
               s.payment_method, s.status
        FROM   sales s
        LEFT JOIN customers c ON s.customer_id = c.id
        {where}
        ORDER BY s.sale_date DESC
    """
    return _df(query, params)


def get_daily_summary(days: int = 30) -> pd.DataFrame:
    query = """
        SELECT DATE(sale_date) AS sale_day,
               COUNT(*)        AS total_sales,
               SUM(net_amount) AS revenue,
               SUM(discount)   AS total_discount
        FROM   sales
        WHERE  sale_date >= CURRENT_DATE - INTERVAL ':days days'
        GROUP BY sale_day
        ORDER BY sale_day
    """
    # Use raw string substitution to avoid bind-parameter issues with INTERVAL
    q = f"""
        SELECT DATE(sale_date) AS sale_day,
               COUNT(*)        AS total_sales,
               SUM(net_amount) AS revenue,
               SUM(discount)   AS total_discount
        FROM   sales
        WHERE  sale_date >= CURRENT_DATE - INTERVAL '{days} days'
        GROUP BY sale_day
        ORDER BY sale_day
    """
    return _df(q)


def get_weekly_summary() -> pd.DataFrame:
    q = """
        SELECT DATE_TRUNC('week', sale_date)::DATE AS week_start,
               COUNT(*)        AS total_sales,
               SUM(net_amount) AS revenue
        FROM   sales
        WHERE  sale_date >= CURRENT_DATE - INTERVAL '12 weeks'
        GROUP BY week_start
        ORDER BY week_start
    """
    return _df(q)


def get_profit_analysis() -> pd.DataFrame:
    q = """
        SELECT p.name                                      AS product,
               SUM(si.quantity)                            AS units_sold,
               SUM(si.total_price)                        AS revenue,
               SUM(si.purchase_price_at_sale * si.quantity) AS cost,
               SUM((si.unit_price - si.purchase_price_at_sale) * si.quantity) AS profit,
               ROUND(
                 100.0 * SUM((si.unit_price - si.purchase_price_at_sale)*si.quantity)
                       / NULLIF(SUM(si.total_price),0), 2
               ) AS margin_pct
        FROM   sale_items si
        JOIN   products p ON si.product_id = p.id
        GROUP BY p.name
        ORDER BY profit DESC
    """
    return _df(q)


def get_profit_by_period(days: int = 30) -> pd.DataFrame:
    q = f"""
        SELECT DATE(s.sale_date) AS sale_day,
               SUM((si.unit_price - si.purchase_price_at_sale)*si.quantity) AS daily_profit,
               SUM(s.net_amount) AS daily_revenue
        FROM   sale_items si
        JOIN   sales s ON si.sale_id = s.id
        WHERE  s.sale_date >= CURRENT_DATE - INTERVAL '{days} days'
        GROUP BY sale_day
        ORDER BY sale_day
    """
    return _df(q)


def get_inventory_status() -> pd.DataFrame:
    q = """
        SELECT p.id, p.name, p.sku,
               COALESCE(c.name,'—') AS category,
               p.stock_quantity, p.min_stock_level,
               p.selling_price, p.purchase_price,
               CASE
                 WHEN p.stock_quantity = 0              THEN 'Out of Stock'
                 WHEN p.stock_quantity <= p.min_stock_level THEN 'Low Stock'
                 ELSE 'OK'
               END AS stock_status
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.is_active = TRUE
        ORDER BY p.stock_quantity ASC
    """
    return _df(q)


def get_top_products(limit: int = 5) -> pd.DataFrame:
    q = f"""
        SELECT p.name AS product,
               SUM(si.quantity) AS units_sold,
               SUM(si.total_price) AS revenue
        FROM sale_items si
        JOIN products p ON si.product_id = p.id
        GROUP BY p.name
        ORDER BY revenue DESC
        LIMIT {limit}
    """
    return _df(q)


def get_dashboard_kpis() -> dict:
    q = """
        SELECT
          (SELECT COALESCE(SUM(net_amount),0) FROM sales
           WHERE DATE(sale_date)=CURRENT_DATE)                AS today_revenue,
          (SELECT COUNT(*) FROM sales
           WHERE DATE(sale_date)=CURRENT_DATE)                AS today_sales,
          (SELECT COALESCE(SUM((si.unit_price-si.purchase_price_at_sale)*si.quantity),0)
           FROM sale_items si JOIN sales s ON si.sale_id=s.id
           WHERE DATE(s.sale_date)=CURRENT_DATE)              AS today_profit,
          (SELECT COUNT(*) FROM products
           WHERE stock_quantity <= min_stock_level
             AND is_active=TRUE)                              AS low_stock_count,
          (SELECT COALESCE(SUM(net_amount),0) FROM sales
           WHERE sale_date >= DATE_TRUNC('month',CURRENT_DATE)) AS month_revenue,
          (SELECT COUNT(*) FROM products WHERE is_active=TRUE)  AS total_products
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(q)
            cols = [d[0] for d in cur.description]
            row  = cur.fetchone()
            return dict(zip(cols, row)) if row else {}
    finally:
        release_connection(conn)


# ══════════════════════════════════════════════════════════════════════════════
# CSV IMPORT / EXPORT
# ══════════════════════════════════════════════════════════════════════════════

def export_products_csv() -> str:
    df = get_all_products()
    return df.to_csv(index=False)


def export_sales_csv(
    start_date=None, end_date=None
) -> str:
    df = get_sales_report(start_date, end_date)
    return df.to_csv(index=False)


def import_products_csv(file_bytes: bytes) -> tuple[int, list[str]]:
    """
    Import products from CSV bytes.
    Expected columns: name, sku, purchase_price, selling_price,
                      stock_quantity, min_stock_level, category
    Returns (success_count, list_of_errors).
    """
    df = pd.read_csv(io.BytesIO(file_bytes))
    required = {"name", "sku", "purchase_price", "selling_price", "stock_quantity"}
    missing  = required - set(df.columns.str.lower())
    if missing:
        return 0, [f"Missing columns: {missing}"]

    df.columns = df.columns.str.lower()
    cats  = get_all_categories()
    cat_map = dict(zip(cats["name"].str.lower(), cats["id"])) if not cats.empty else {}

    ok, errors = 0, []
    for _, row in df.iterrows():
        cat_name = str(row.get("category", "")).strip().lower()
        cat_id   = cat_map.get(cat_name)
        if not cat_id and cat_name:
            add_category(cat_name.title())
            cats    = get_all_categories()
            cat_map = dict(zip(cats["name"].str.lower(), cats["id"]))
            cat_id  = cat_map.get(cat_name)

        success, msg = add_product(
            category_id    = cat_id,
            name           = str(row["name"]),
            sku            = str(row["sku"]),
            purchase_price = float(row["purchase_price"]),
            selling_price  = float(row["selling_price"]),
            stock_quantity = int(row.get("stock_quantity", 0)),
            min_stock_level= int(row.get("min_stock_level", 10)),
        )
        if success:
            ok += 1
        else:
            errors.append(f"Row '{row['name']}': {msg}")

    return ok, errors
