"""
tests/test_backend.py — Unit tests for the Retail Analytics backend
Run: python -m pytest tests/test_backend.py -v
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from backend import (
    add_category, get_all_categories,
    add_product, get_all_products, get_product_by_id,
    restock_product, delete_product,
    add_customer, get_all_customers,
    process_sale, get_profit_analysis, get_sales_report,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_category():
    """Create a test category and return its ID."""
    name = "_TEST_CAT_PYTEST_"
    cats_before = get_all_categories()
    existing = cats_before[cats_before["name"] == name] if not cats_before.empty else None
    if existing is not None and not existing.empty:
        return int(existing.iloc[0]["id"])
    ok = add_category(name, "Pytest test category")
    assert ok, "Failed to add test category"
    cats = get_all_categories()
    row  = cats[cats["name"] == name]
    assert not row.empty
    return int(row.iloc[0]["id"])


@pytest.fixture(scope="session")
def test_product(test_category):
    """Create a test product and return its ID."""
    ok, msg = add_product(
        category_id=test_category,
        name="_TEST_PRODUCT_",
        sku="_TEST-SKU-001_",
        purchase_price=50.0,
        selling_price=100.0,
        stock_quantity=100,
        min_stock_level=5,
    )
    assert ok, f"add_product failed: {msg}"
    products = get_all_products()
    row = products[products["sku"] == "_TEST-SKU-001_"]
    assert not row.empty
    return int(row.iloc[0]["id"])


@pytest.fixture(scope="session")
def test_customer():
    """Create a test customer and return ID."""
    cid, msg = add_customer("_Test Customer_", "9999999999", "test@pytest.local")
    assert cid is not None, f"add_customer failed: {msg}"
    return cid


# ─── Category tests ────────────────────────────────────────────────────────────

def test_add_category_duplicate():
    """Duplicate category names should fail gracefully."""
    add_category("_DUPE_CAT_TEST_")
    result = add_category("_DUPE_CAT_TEST_")
    assert result is False  # Must return False on duplicate


def test_get_all_categories_returns_dataframe():
    import pandas as pd
    df = get_all_categories()
    assert isinstance(df, pd.DataFrame)


# ─── Product tests ─────────────────────────────────────────────────────────────

def test_get_product_by_id(test_product):
    prod = get_product_by_id(test_product)
    assert prod is not None
    assert prod["sku"] == "_TEST-SKU-001_"
    assert prod["selling_price"] == 100.0
    assert prod["purchase_price"] == 50.0


def test_add_product_duplicate_sku(test_category):
    """Duplicate SKU must fail."""
    ok, msg = add_product(test_category, "Duplicate", "_TEST-SKU-001_", 10, 20, 5, 1)
    assert not ok, "Duplicate SKU should not succeed"


def test_restock_product(test_product):
    prod_before = get_product_by_id(test_product)
    stock_before = prod_before["stock_quantity"]
    ok, msg = restock_product(test_product, 20, "Test restock")
    assert ok, f"Restock failed: {msg}"
    prod_after = get_product_by_id(test_product)
    assert prod_after["stock_quantity"] == stock_before + 20


def test_restock_zero_or_negative_fails(test_product):
    ok, _ = restock_product(test_product, 0)
    assert not ok
    ok2, _ = restock_product(test_product, -5)
    assert not ok2


# ─── Billing & stock safety tests ─────────────────────────────────────────────

def test_process_sale_success(test_product, test_customer):
    prod = get_product_by_id(test_product)
    stock_before = prod["stock_quantity"]
    qty = 3

    ok, sale_id = process_sale(
        customer_id=test_customer,
        cart_items=[{
            "product_id":    test_product,
            "quantity":      qty,
            "unit_price":    100.0,
            "purchase_price":50.0,
        }],
        discount=0,
        payment_method="Cash",
    )
    assert ok, f"process_sale failed: {sale_id}"
    assert isinstance(sale_id, int)

    prod_after = get_product_by_id(test_product)
    assert prod_after["stock_quantity"] == stock_before - qty, "Stock not decremented correctly"


def test_process_sale_insufficient_stock(test_product, test_customer):
    """Selling more than available stock must fail — stock must not go negative."""
    prod = get_product_by_id(test_product)
    excess_qty = prod["stock_quantity"] + 9999

    ok, result = process_sale(
        customer_id=test_customer,
        cart_items=[{
            "product_id":    test_product,
            "quantity":      excess_qty,
            "unit_price":    100.0,
            "purchase_price":50.0,
        }],
    )
    assert not ok, "Sale with excess stock must fail"

    # Verify stock did NOT go negative
    prod_after = get_product_by_id(test_product)
    assert prod_after["stock_quantity"] >= 0, "Stock went negative — CRITICAL BUG"


def test_process_sale_empty_cart(test_customer):
    ok, msg = process_sale(customer_id=test_customer, cart_items=[])
    assert not ok
    assert "empty" in str(msg).lower()


# ─── Analytics tests ──────────────────────────────────────────────────────────

def test_get_profit_analysis_returns_dataframe():
    import pandas as pd
    df = get_profit_analysis()
    assert isinstance(df, pd.DataFrame)
    if not df.empty:
        assert "profit" in df.columns
        assert "margin_pct" in df.columns
        # Profit = revenue - cost
        for _, row in df.iterrows():
            expected = round(float(row["revenue"]) - float(row["cost"]), 2)
            actual   = round(float(row["profit"]), 2)
            assert abs(expected - actual) < 0.05, f"Profit mismatch for {row['product']}"


def test_get_sales_report_returns_dataframe():
    import pandas as pd
    df = get_sales_report()
    assert isinstance(df, pd.DataFrame)


def test_stock_never_negative():
    """Comprehensive check: all products have non-negative stock."""
    products = get_all_products()
    if not products.empty:
        assert (products["stock_quantity"] >= 0).all(), \
            "Found products with negative stock!"
