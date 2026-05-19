"""
pages/3_📊_Sales_Report.py — Daily/Weekly Sales Reports
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import datetime
from backend import get_sales_report, get_daily_summary, get_weekly_summary
from utils.helpers import fmt_currency, page_header, warn

st.set_page_config(page_title="Sales Report", page_icon="📊", layout="wide")

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

page_header("📊 Sales Reports", "Daily and weekly revenue analysis with date filters")

# ── Date filters ───────────────────────────────────────────────────────────────
f1, f2, f3 = st.columns([1, 1, 2])
with f1:
    start_date = st.date_input("From", value=datetime.date.today() - datetime.timedelta(days=30))
with f2:
    end_date = st.date_input("To", value=datetime.date.today())
with f3:
    quick = st.radio("Quick select", ["Custom", "Today", "Last 7 Days", "This Month"],
                     horizontal=True, label_visibility="collapsed")

today = datetime.date.today()
if quick == "Today":
    start_date = end_date = today
elif quick == "Last 7 Days":
    start_date = today - datetime.timedelta(days=7)
    end_date   = today
elif quick == "This Month":
    start_date = today.replace(day=1)
    end_date   = today

st.divider()

# ── KPIs for period ────────────────────────────────────────────────────────────
sales_df = get_sales_report(start_date, end_date)

if sales_df.empty:
    warn("No sales data for the selected period.")
else:
    total_revenue  = sales_df["net_amount"].sum()
    total_discount = sales_df["discount"].sum()
    total_txn      = len(sales_df)
    avg_order      = total_revenue / total_txn if total_txn else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 Total Revenue",   fmt_currency(total_revenue))
    m2.metric("🧾 Transactions",    str(total_txn))
    m3.metric("🛒 Avg Order Value", fmt_currency(avg_order))
    m4.metric("🏷️ Total Discount",  fmt_currency(total_discount))

    st.divider()

    # ── Daily revenue bar chart ────────────────────────────────────────────────
    st.markdown("### 📅 Daily Revenue")
    daily = get_daily_summary(days=(end_date - start_date).days + 1)
    if not daily.empty:
        fig_daily = px.bar(
            daily, x="sale_day", y="revenue",
            labels={"sale_day": "Date", "revenue": "Revenue (₹)", "total_sales": "Transactions"},
            color_discrete_sequence=["#6366f1"],
            template="plotly_dark",
            hover_data=["total_sales", "total_discount"],
        )
        fig_daily.update_layout(
            plot_bgcolor="#1e293b", paper_bgcolor="#1e293b",
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(gridcolor="#334155"),
            yaxis=dict(gridcolor="#334155"),
        )
        st.plotly_chart(fig_daily, use_container_width=True)

    # ── Weekly trend line ──────────────────────────────────────────────────────
    st.markdown("### 📆 Weekly Revenue Trend")
    weekly = get_weekly_summary()
    if not weekly.empty:
        fig_weekly = go.Figure()
        fig_weekly.add_trace(go.Scatter(
            x=weekly["week_start"], y=weekly["revenue"],
            mode="lines+markers",
            line=dict(color="#8b5cf6", width=3),
            marker=dict(size=8, color="#6366f1"),
            fill="tozeroy", fillcolor="rgba(99,102,241,0.15)",
            name="Revenue",
        ))
        fig_weekly.update_layout(
            template="plotly_dark",
            plot_bgcolor="#1e293b", paper_bgcolor="#1e293b",
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(gridcolor="#334155", title="Week"),
            yaxis=dict(gridcolor="#334155", title="Revenue (₹)"),
        )
        st.plotly_chart(fig_weekly, use_container_width=True)

    # ── Transactions table ─────────────────────────────────────────────────────
    st.markdown("### 📋 Transactions")

    # Payment method breakdown
    pay_col1, pay_col2 = st.columns([2, 1])
    with pay_col2:
        pay_dist = sales_df.groupby("payment_method")["net_amount"].sum().reset_index()
        if not pay_dist.empty:
            fig_pay = px.pie(
                pay_dist, names="payment_method", values="net_amount",
                hole=0.5, template="plotly_dark",
                color_discrete_sequence=["#6366f1","#8b5cf6","#a78bfa","#c4b5fd"],
                title="Payment Methods",
            )
            fig_pay.update_layout(paper_bgcolor="#1e293b", margin=dict(l=0,r=0,t=30,b=0))
            st.plotly_chart(fig_pay, use_container_width=True)

    with pay_col1:
        st.dataframe(
            sales_df[["sale_id", "sale_date", "customer", "net_amount", "discount", "payment_method", "status"]]
            .rename(columns={
                "sale_id": "Sale #", "sale_date": "Date", "customer": "Customer",
                "net_amount": "Amount (₹)", "discount": "Discount",
                "payment_method": "Payment", "status": "Status",
            }),
            use_container_width=True, hide_index=True,
        )

    # Export
    csv_bytes = sales_df.to_csv(index=False).encode()
    st.download_button("⬇️ Export Sales CSV", csv_bytes, "sales_report.csv", "text/csv")
