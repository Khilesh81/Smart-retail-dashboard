"""
pages/1_📦_Inventory.py — Inventory Tracking & Product CRUD
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
from backend import (
    get_all_products, get_all_categories, add_product,
    update_product, delete_product, restock_product, get_product_by_id,
)
from utils.helpers import fmt_currency, stock_badge, page_header, success, error, warn
import pandas as pd

st.set_page_config(page_title="Inventory", page_icon="📦", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.stApp{background-color:#0f172a;color:#e2e8f0;}
h1,h2,h3{color:#f8fafc!important;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0f172a 0%,#1e293b 100%);}
[data-testid="stSidebar"] *{color:#e2e8f0!important;}
.stButton>button{background:linear-gradient(135deg,#6366f1,#8b5cf6);color:white;border:none;border-radius:8px;font-weight:600;}
hr{border-color:#334155!important;}
</style>
""", unsafe_allow_html=True)

page_header("📦 Inventory Management", "Track stock levels, add/edit products, restock")

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_view, tab_add, tab_edit, tab_restock = st.tabs(
    ["📋 Stock View", "➕ Add Product", "✏️ Edit / Delete", "🔄 Restock"]
)

# ── TAB 1: Stock View ─────────────────────────────────────────────────────────
with tab_view:
    df = get_all_products()
    if df.empty:
        warn("No products found. Add products in the 'Add Product' tab.")
    else:
        # Summary metrics
        total    = len(df)
        low_st   = len(df[df["stock_quantity"] <= df["min_stock_level"]])
        out_st   = len(df[df["stock_quantity"] == 0])
        m1,m2,m3 = st.columns(3)
        m1.metric("Total Products", total)
        m2.metric("⚠️ Low Stock",   low_st)
        m3.metric("🔴 Out of Stock", out_st)

        st.markdown("---")

        # Filter
        col_f1, col_f2 = st.columns([2,1])
        with col_f1:
            search = st.text_input("🔍 Search by name or SKU", "")
        with col_f2:
            status_filter = st.selectbox("Filter by status", ["All", "OK", "Low Stock", "Out of Stock"])

        # Add status column
        def classify(row):
            if row["stock_quantity"] == 0:               return "Out of Stock"
            if row["stock_quantity"] <= row["min_stock_level"]: return "Low Stock"
            return "OK"

        df["Status"] = df.apply(classify, axis=1)

        if search:
            mask = (df["name"].str.contains(search, case=False, na=False) |
                    df["sku"].str.contains(search, case=False, na=False))
            df = df[mask]
        if status_filter != "All":
            df = df[df["Status"] == status_filter]

        # Display
        display_cols = ["id", "name", "sku", "category", "purchase_price",
                        "selling_price", "stock_quantity", "min_stock_level", "Status"]
        st.dataframe(
            df[display_cols].rename(columns={
                "id": "ID", "name": "Product", "sku": "SKU",
                "category": "Category", "purchase_price": "Cost (₹)",
                "selling_price": "Price (₹)", "stock_quantity": "Stock",
                "min_stock_level": "Min Level",
            }),
            use_container_width=True,
            hide_index=True,
        )

        # Export
        csv = df.to_csv(index=False).encode()
        st.download_button("⬇️ Export CSV", csv, "inventory.csv", "text/csv")

# ── TAB 2: Add Product ────────────────────────────────────────────────────────
with tab_add:
    cats = get_all_categories()
    cat_options = {row["name"]: row["id"] for _, row in cats.iterrows()} if not cats.empty else {}

    if not cat_options:
        warn("No categories yet. Go to ⚙️ Settings to add one first.")
    else:
        with st.form("add_product_form", clear_on_submit=True):
            st.markdown("#### New Product Details")
            c1, c2 = st.columns(2)
            with c1:
                p_name    = st.text_input("Product Name *", placeholder="e.g. Basmati Rice 5kg")
                p_sku     = st.text_input("SKU *", placeholder="e.g. RICE-5KG")
                p_cat     = st.selectbox("Category *", list(cat_options.keys()))
                p_stock   = st.number_input("Initial Stock *", min_value=0, value=50)
            with c2:
                p_cost    = st.number_input("Purchase Price (₹) *", min_value=0.0, step=0.5, format="%.2f")
                p_price   = st.number_input("Selling Price (₹) *",  min_value=0.0, step=0.5, format="%.2f")
                p_min     = st.number_input("Min Stock Level",       min_value=0, value=10)

            submitted = st.form_submit_button("➕ Add Product", use_container_width=True)
            if submitted:
                if not p_name or not p_sku:
                    error("Name and SKU are required.")
                elif p_price < p_cost:
                    warn("Selling price is less than purchase price — margin will be negative.")
                    ok, msg = add_product(cat_options[p_cat], p_name, p_sku, p_cost, p_price, p_stock, p_min)
                    (success if ok else error)(msg)
                else:
                    ok, msg = add_product(cat_options[p_cat], p_name, p_sku, p_cost, p_price, p_stock, p_min)
                    (success if ok else error)(msg)

# ── TAB 3: Edit / Delete ──────────────────────────────────────────────────────
with tab_edit:
    df_edit = get_all_products()
    if df_edit.empty:
        warn("No products to edit.")
    else:
        cats = get_all_categories()
        cat_options = {row["name"]: row["id"] for _, row in cats.iterrows()} if not cats.empty else {}
        cat_by_id   = {v: k for k, v in cat_options.items()}

        prod_map = {f"{r['name']} ({r['sku']})": r["id"] for _, r in df_edit.iterrows()}
        selected = st.selectbox("Select product to edit", list(prod_map.keys()))

        if selected:
            pid  = prod_map[selected]
            prod = get_product_by_id(pid)

            if prod:
                with st.form("edit_product_form"):
                    st.markdown("#### Edit Product")
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        e_name  = st.text_input("Name",  value=prod["name"])
                        e_sku   = st.text_input("SKU",   value=prod["sku"])
                        e_cat   = st.selectbox("Category",
                                               list(cat_options.keys()),
                                               index=list(cat_options.values()).index(prod["category_id"])
                                               if prod["category_id"] in cat_options.values() else 0)
                        e_active = st.checkbox("Active", value=bool(prod["is_active"]))
                    with ec2:
                        e_cost  = st.number_input("Purchase Price (₹)", value=float(prod["purchase_price"]), step=0.5, format="%.2f")
                        e_price = st.number_input("Selling Price (₹)",  value=float(prod["selling_price"]),  step=0.5, format="%.2f")
                        e_min   = st.number_input("Min Stock Level",     value=int(prod["min_stock_level"]),  min_value=0)

                    col_upd, col_del = st.columns(2)
                    with col_upd:
                        if st.form_submit_button("💾 Save Changes", use_container_width=True):
                            ok, msg = update_product(pid, cat_options[e_cat], e_name, e_sku, e_cost, e_price, e_min, e_active)
                            (success if ok else error)(msg)
                    with col_del:
                        if st.form_submit_button("🗑️ Delete Product", use_container_width=True):
                            ok, msg = delete_product(pid)
                            (success if ok else error)(msg)

# ── TAB 4: Restock ────────────────────────────────────────────────────────────
with tab_restock:
    df_r = get_all_products()
    if df_r.empty:
        warn("No products available.")
    else:
        prod_map_r = {f"{r['name']} ({r['sku']}) — Stock: {r['stock_quantity']}": r["id"]
                      for _, r in df_r.iterrows()}
        sel_r = st.selectbox("Select product to restock", list(prod_map_r.keys()))
        with st.form("restock_form", clear_on_submit=True):
            r_qty   = st.number_input("Quantity to Add", min_value=1, value=50)
            r_notes = st.text_input("Notes (optional)", placeholder="Supplier delivery, PO #1234")
            if st.form_submit_button("🔄 Restock", use_container_width=True):
                ok, msg = restock_product(prod_map_r[sel_r], r_qty, r_notes)
                (success if ok else error)(msg)
