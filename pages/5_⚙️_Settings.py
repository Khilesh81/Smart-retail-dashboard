"""
pages/5_⚙️_Settings.py — Categories, CSV Import/Export, DB Management
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
from backend import (
    get_all_categories, add_category, delete_category,
    export_products_csv, export_sales_csv,
    import_products_csv, get_all_customers, add_customer,
)
from utils.helpers import page_header, success, error, warn

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")

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

page_header("⚙️ Settings", "Manage categories, import/export data, and configure the system")

tab_cat, tab_cust, tab_import, tab_export = st.tabs(
    ["📂 Categories", "👥 Customers", "📥 CSV Import", "📤 CSV Export"]
)

# ── TAB 1: Categories ─────────────────────────────────────────────────────────
with tab_cat:
    st.markdown("### 📂 Product Categories")

    cats = get_all_categories()
    if not cats.empty:
        st.dataframe(
            cats[["id", "name", "description"]].rename(
                columns={"id": "ID", "name": "Category", "description": "Description"}
            ),
            use_container_width=True, hide_index=True,
        )
    else:
        warn("No categories yet.")

    st.divider()
    st.markdown("#### ➕ Add Category")
    with st.form("add_cat_form", clear_on_submit=True):
        c_name = st.text_input("Category Name *", placeholder="e.g. Beverages")
        c_desc = st.text_area("Description", placeholder="Optional description", height=80)
        if st.form_submit_button("Add Category", use_container_width=True):
            if c_name:
                ok = add_category(c_name, c_desc)
                (success if ok else error)("Category added." if ok else "Category may already exist.")
            else:
                error("Category name is required.")

    if not cats.empty:
        st.divider()
        st.markdown("#### 🗑️ Delete Category")
        cat_del_map = {row["name"]: row["id"] for _, row in cats.iterrows()}
        del_cat = st.selectbox("Select category to delete", list(cat_del_map.keys()))
        st.warning("⚠️ Deleting a category will set associated products' category to null.")
        if st.button("Delete Selected Category"):
            ok = delete_category(cat_del_map[del_cat])
            (success if ok else error)("Category deleted." if ok else "Error deleting category.")

# ── TAB 2: Customers ──────────────────────────────────────────────────────────
with tab_cust:
    st.markdown("### 👥 Customer Management")
    customers = get_all_customers()
    non_walkin = customers[customers["email"] != "walkin@store.local"] if not customers.empty else customers

    if not non_walkin.empty:
        st.dataframe(
            non_walkin[["id", "name", "phone", "email", "created_at"]].rename(
                columns={"id": "ID", "name": "Name", "phone": "Phone",
                         "email": "Email", "created_at": "Joined"}
            ),
            use_container_width=True, hide_index=True,
        )
    else:
        warn("No named customers yet.")

    st.divider()
    st.markdown("#### ➕ Add Customer")
    with st.form("add_cust_form", clear_on_submit=True):
        cu1, cu2, cu3 = st.columns(3)
        cu_name  = cu1.text_input("Full Name *")
        cu_phone = cu2.text_input("Phone")
        cu_email = cu3.text_input("Email")
        if st.form_submit_button("Add Customer", use_container_width=True):
            if cu_name:
                cid, msg = add_customer(cu_name, cu_phone, cu_email)
                (success if cid else error)(f"Customer added (ID: {cid})." if cid else msg)
            else:
                error("Name is required.")

# ── TAB 3: CSV Import ─────────────────────────────────────────────────────────
with tab_import:
    st.markdown("### 📥 Import Products from CSV")
    st.markdown("""
    **Required columns:**
    `name`, `sku`, `purchase_price`, `selling_price`, `stock_quantity`

    **Optional columns:**
    `min_stock_level`, `category`
    """)

    # Sample CSV download
    sample_csv = """name,sku,purchase_price,selling_price,stock_quantity,min_stock_level,category
Basmati Rice 5kg,RICE-5KG,250.00,320.00,100,20,Grains
Refined Oil 1L,OIL-1L,130.00,165.00,75,15,Cooking
Toor Dal 1kg,DAL-TOOR-1KG,110.00,140.00,60,10,Pulses
"""
    st.download_button(
        "⬇️ Download Sample CSV",
        sample_csv.encode(),
        "sample_products.csv",
        "text/csv",
    )

    uploaded = st.file_uploader("Upload Products CSV", type=["csv"])
    if uploaded:
        with st.expander("Preview uploaded file"):
            import pandas as pd
            preview = pd.read_csv(uploaded)
            st.dataframe(preview.head(10), use_container_width=True)
            uploaded.seek(0)

        if st.button("📥 Import Products", use_container_width=True):
            file_bytes = uploaded.read()
            ok_count, errors_list = import_products_csv(file_bytes)
            if ok_count:
                success(f"Imported {ok_count} products successfully.")
            if errors_list:
                for err_msg in errors_list:
                    error(err_msg)

# ── TAB 4: CSV Export ─────────────────────────────────────────────────────────
with tab_export:
    st.markdown("### 📤 Export Data to CSV")

    col_exp1, col_exp2 = st.columns(2)

    with col_exp1:
        st.markdown("#### 📦 Products")
        prod_csv = export_products_csv()
        st.download_button(
            "⬇️ Export All Products",
            prod_csv.encode(),
            "products_export.csv",
            "text/csv",
            use_container_width=True,
        )

    with col_exp2:
        st.markdown("#### 🧾 Sales")
        import datetime
        exp_start = st.date_input("From", value=datetime.date.today() - datetime.timedelta(days=30),
                                   key="exp_start")
        exp_end   = st.date_input("To",   value=datetime.date.today(), key="exp_end")
        sales_csv = export_sales_csv(exp_start, exp_end)
        st.download_button(
            "⬇️ Export Sales Report",
            sales_csv.encode(),
            "sales_export.csv",
            "text/csv",
            use_container_width=True,
        )
