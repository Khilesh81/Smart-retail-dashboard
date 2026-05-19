"""
pages/2_🧾_Billing.py — POS / Billing System
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
from backend import (
    get_all_products, get_all_customers, add_customer,
    process_sale, get_sale_receipt,
)
from utils.helpers import fmt_currency, page_header, success, error, warn
import datetime

st.set_page_config(page_title="Billing", page_icon="🧾", layout="wide")

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
.cart-item{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:12px;margin-bottom:8px;}
</style>
""", unsafe_allow_html=True)

page_header("🧾 Billing / POS", "Process sales, manage cart, generate receipts")

# ── Session state for cart ────────────────────────────────────────────────────
if "cart" not in st.session_state:
    st.session_state["cart"] = []   # list of dicts
if "last_sale_id" not in st.session_state:
    st.session_state["last_sale_id"] = None

# ── Layout ────────────────────────────────────────────────────────────────────
left, right = st.columns([3, 2])

with left:
    st.markdown("### 🛒 Add Items to Cart")

    # Customer
    st.markdown("#### 👤 Customer")
    cust_mode = st.radio("Customer type", ["Walk-in", "Existing", "New"], horizontal=True, label_visibility="collapsed")

    customer_id = None
    customers_df = get_all_customers()

    if cust_mode == "Walk-in":
        walkin = customers_df[customers_df["email"] == "walkin@store.local"]
        customer_id = int(walkin.iloc[0]["id"]) if not walkin.empty else None
        st.caption("Using Walk-in Customer")

    elif cust_mode == "Existing":
        if not customers_df.empty:
            cust_map = {f"{r['name']} ({r['phone'] or 'N/A'})": r["id"]
                        for _, r in customers_df.iterrows()
                        if r["email"] != "walkin@store.local"}
            if cust_map:
                sel_cust = st.selectbox("Select customer", list(cust_map.keys()))
                customer_id = cust_map[sel_cust]
            else:
                warn("No named customers yet. Use 'New' to add one.")
        else:
            warn("No customers in database.")

    else:  # New
        with st.form("new_customer_form", clear_on_submit=True):
            nc1, nc2, nc3 = st.columns(3)
            n_name  = nc1.text_input("Name *")
            n_phone = nc2.text_input("Phone")
            n_email = nc3.text_input("Email")
            if st.form_submit_button("➕ Add Customer"):
                if n_name:
                    cid, msg = add_customer(n_name, n_phone, n_email)
                    if cid:
                        st.session_state["_new_cust_id"] = cid
                        success(f"Customer added: {n_name}")
                    else:
                        error(msg)
                else:
                    error("Name is required.")
        customer_id = st.session_state.get("_new_cust_id")

    st.divider()

    # Product picker
    st.markdown("#### 📦 Add Product")
    products_df = get_all_products()
    if products_df.empty:
        warn("No products found. Please add products first.")
    else:
        active_df = products_df[products_df["is_active"] == True]
        prod_options = {
            f"{r['name']} ({r['sku']}) — Stock: {r['stock_quantity']} — ₹{r['selling_price']}": {
                "id": r["id"], "name": r["name"], "sku": r["sku"],
                "selling_price": float(r["selling_price"]),
                "purchase_price": float(r["purchase_price"]),
                "stock": int(r["stock_quantity"]),
            }
            for _, r in active_df.iterrows()
        }

        with st.form("add_item_form", clear_on_submit=True):
            selected_prod_key = st.selectbox("Select product", list(prod_options.keys()))
            item_qty = st.number_input("Quantity", min_value=1, value=1)
            if st.form_submit_button("➕ Add to Cart", use_container_width=True):
                prod_info = prod_options[selected_prod_key]
                if item_qty > prod_info["stock"]:
                    error(f"Only {prod_info['stock']} in stock.")
                else:
                    # Check if already in cart
                    existing = next((i for i in st.session_state["cart"]
                                     if i["product_id"] == prod_info["id"]), None)
                    if existing:
                        existing["quantity"] += item_qty
                    else:
                        st.session_state["cart"].append({
                            "product_id":    prod_info["id"],
                            "name":          prod_info["name"],
                            "sku":           prod_info["sku"],
                            "unit_price":    prod_info["selling_price"],
                            "purchase_price":prod_info["purchase_price"],
                            "quantity":      item_qty,
                        })
                    success(f"Added {item_qty}× {prod_info['name']}")


with right:
    st.markdown("### 🧾 Cart")

    if not st.session_state["cart"]:
        st.info("Cart is empty. Add products from the left panel.")
    else:
        # Cart items
        items_to_remove = []
        for idx, item in enumerate(st.session_state["cart"]):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            c1.markdown(f"**{item['name']}** `{item['sku']}`")
            qty = c2.number_input("Qty", min_value=1, value=item["quantity"],
                                  key=f"qty_{idx}", label_visibility="collapsed")
            st.session_state["cart"][idx]["quantity"] = qty
            subtotal = item["unit_price"] * qty
            c3.markdown(f"<div style='padding-top:8px'>{fmt_currency(subtotal)}</div>",
                        unsafe_allow_html=True)
            if c4.button("🗑️", key=f"del_{idx}"):
                items_to_remove.append(idx)

        for i in reversed(items_to_remove):
            st.session_state["cart"].pop(i)
            st.rerun()

        st.divider()

        # Totals
        subtotal_total = sum(i["unit_price"] * i["quantity"] for i in st.session_state["cart"])
        discount       = st.number_input("Discount (₹)", min_value=0.0, step=10.0,
                                         max_value=float(subtotal_total), format="%.2f")
        net_total      = max(0.0, subtotal_total - discount)
        payment_method = st.selectbox("Payment Method", ["Cash", "UPI", "Card", "Credit"])

        st.markdown(f"""
        | | Amount |
        |---|---|
        | Subtotal | {fmt_currency(subtotal_total)} |
        | Discount | − {fmt_currency(discount)} |
        | **Net Total** | **{fmt_currency(net_total)}** |
        """)

        col_proc, col_clr = st.columns(2)
        with col_proc:
            if st.button("✅ Process Sale", use_container_width=True, type="primary"):
                if not customer_id:
                    error("Please select a customer first.")
                else:
                    ok, result = process_sale(
                        customer_id  = customer_id,
                        cart_items   = st.session_state["cart"],
                        discount     = discount,
                        payment_method = payment_method,
                    )
                    if ok:
                        st.session_state["last_sale_id"] = result
                        st.session_state["cart"] = []
                        st.session_state.pop("_new_cust_id", None)
                        success(f"Sale #{result} completed!")
                        st.rerun()
                    else:
                        error(f"Sale failed: {result}")
        with col_clr:
            if st.button("🗑️ Clear Cart", use_container_width=True):
                st.session_state["cart"] = []
                st.rerun()

# ── Receipt ───────────────────────────────────────────────────────────────────
if st.session_state["last_sale_id"]:
    st.divider()
    receipt = get_sale_receipt(st.session_state["last_sale_id"])
    if receipt:
        st.markdown("### 🧾 Receipt")
        r1, r2, r3 = st.columns(3)
        r1.markdown(f"**Sale ID:** #{receipt['id']}")
        r2.markdown(f"**Customer:** {receipt.get('customer_name', 'Walk-in')}")
        r3.markdown(f"**Date:** {str(receipt['sale_date'])[:19]}")

        for itm in receipt.get("items", []):
            st.markdown(
                f"- {itm['product_name']} ({itm['sku']}) × {itm['quantity']}"
                f" = {fmt_currency(itm['total_price'])}"
            )

        st.markdown(f"""
        | | |
        |---|---|
        | Total | {fmt_currency(receipt['total_amount'])} |
        | Discount | − {fmt_currency(receipt['discount'])} |
        | **Net Paid** | **{fmt_currency(receipt['net_amount'])}** |
        | Method | {receipt['payment_method']} |
        """)

        if st.button("🔄 New Sale"):
            st.session_state["last_sale_id"] = None
            st.rerun()
