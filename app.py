"""
app.py — Retail Store Analytics System
Streamlit entry point with dashboard home page.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

st.set_page_config(
    page_title="Retail Analytics",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
}
[data-testid="stSidebar"] * {color: #e2e8f0 !important;}

/* Metric cards */
[data-testid="metric-container"] {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 16px;
}

/* Buttons */
.stButton>button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    padding: 0.4rem 1.2rem;
    transition: opacity 0.2s;
}
.stButton>button:hover {opacity: 0.85;}

/* Data tables */
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

/* Page background */
.stApp { background-color: #0f172a; color: #e2e8f0; }

/* Headers */
h1,h2,h3 { color: #f8fafc !important; }

/* Divider */
hr { border-color: #334155 !important; }
</style>
""", unsafe_allow_html=True)

# ── DB Init (once per session) ───────────────────────────────────────────────
if "db_initialized" not in st.session_state:
    try:
        from database import init_db
        init_db()
        st.session_state["db_initialized"] = True
    except Exception as e:
        st.session_state["db_initialized"] = False
        st.session_state["db_error"] = str(e)

if not st.session_state.get("db_initialized"):
    err = st.session_state.get("db_error", "Unknown error")
    st.markdown("## ⚠️ Database Not Connected")
    st.error(f"**Error:** {err}")
    st.markdown("""
---
### 🛠️ Fix: Start PostgreSQL

**Step 1 — Install PostgreSQL** (if not installed):
```
winget install --id PostgreSQL.PostgreSQL.17 --exact --accept-source-agreements
```

**Step 2 — Start the PostgreSQL service:**
```
net start postgresql-x64-17
```

**Step 3 — Create the database** (in `psql` or pgAdmin):
```sql
CREATE DATABASE retail_db;
```

**Step 4 — Update your `.env` file** in the project folder:
```
DB_HOST=localhost
DB_NAME=retail_db
DB_USER=postgres
DB_PASSWORD=your_actual_password
DB_PORT=5432
```

**Step 5 — Reload this page** after starting PostgreSQL.
""")
    if st.button("🔄 Retry Connection"):
        st.session_state.pop("db_initialized", None)
        st.session_state.pop("db_error", None)
        st.rerun()
    st.stop()

# ── Home Dashboard ───────────────────────────────────────────────────────────
from backend import get_dashboard_kpis, get_daily_summary, get_top_products
from utils.helpers import fmt_currency, fmt_pct
import plotly.express as px

st.markdown("# 🛒 Retail Store Analytics")
st.markdown("<p style='color:#94a3b8;margin-top:-12px'>Your real-time retail command center</p>",
            unsafe_allow_html=True)
st.divider()

# KPIs
kpis = get_dashboard_kpis()
k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1: st.metric("💰 Today Revenue",  fmt_currency(kpis.get("today_revenue", 0)))
with k2: st.metric("🧾 Today Sales",    str(kpis.get("today_sales", 0)))
with k3: st.metric("📈 Today Profit",   fmt_currency(kpis.get("today_profit", 0)))
with k4: st.metric("📦 Low Stock",      str(kpis.get("low_stock_count", 0)))
with k5: st.metric("🗓️ Month Revenue",  fmt_currency(kpis.get("month_revenue", 0)))
with k6: st.metric("🏷️ Products",       str(kpis.get("total_products", 0)))

st.divider()

col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown("### 📊 Revenue — Last 30 Days")
    daily = get_daily_summary(30)
    if not daily.empty:
        fig = px.bar(
            daily, x="sale_day", y="revenue",
            labels={"sale_day": "Date", "revenue": "Revenue (₹)"},
            color_discrete_sequence=["#6366f1"],
            template="plotly_dark",
        )
        fig.update_layout(
            plot_bgcolor="#1e293b", paper_bgcolor="#1e293b",
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(gridcolor="#334155"),
            yaxis=dict(gridcolor="#334155"),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No sales data yet. Start by adding products and processing sales.")

with col_right:
    st.markdown("### 🏆 Top 5 Products")
    top = get_top_products(5)
    if not top.empty:
        fig2 = px.pie(
            top, names="product", values="revenue",
            hole=0.5, template="plotly_dark",
            color_discrete_sequence=px.colors.sequential.Purpor,
        )
        fig2.update_layout(
            paper_bgcolor="#1e293b",
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(font=dict(color="#e2e8f0")),
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No product sales yet.")

st.divider()
st.markdown(
    "<p style='text-align:center;color:#475569;font-size:13px'>"
    "Retail Analytics MVP • Built with Streamlit + PostgreSQL</p>",
    unsafe_allow_html=True,
)
