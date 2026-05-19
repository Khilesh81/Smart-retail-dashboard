"""
pages/4_💰_Profit.py — Profit Analysis Dashboard
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from backend import get_profit_analysis, get_profit_by_period
from utils.helpers import fmt_currency, fmt_pct, page_header, warn

st.set_page_config(page_title="Profit Analysis", page_icon="💰", layout="wide")

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

page_header("💰 Profit Analysis", "Margin tracking, top/bottom performers, period trends")

# Period toggle
days_opt = st.radio("Analysis period", [7, 30, 90], horizontal=True,
                    format_func=lambda x: f"Last {x} days", label_visibility="collapsed")

st.divider()

profit_df  = get_profit_analysis()
period_df  = get_profit_by_period(days_opt)

if profit_df.empty:
    warn("No sales data available. Process some sales to see profit analysis.")
    st.stop()

# ── KPIs ───────────────────────────────────────────────────────────────────────
total_revenue = float(profit_df["revenue"].sum())
total_cost    = float(profit_df["cost"].sum())
total_profit  = float(profit_df["profit"].sum())
avg_margin    = (total_profit / total_revenue * 100) if total_revenue else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("💰 Total Revenue", fmt_currency(total_revenue))
k2.metric("📦 Total Cost",    fmt_currency(total_cost))
k3.metric("📈 Total Profit",  fmt_currency(total_profit))
k4.metric("📊 Avg Margin",    fmt_pct(avg_margin))

st.divider()

# ── Profit by product bar chart ────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 🏷️ Profit by Product")
    fig_prod = px.bar(
        profit_df.sort_values("profit", ascending=True),
        x="profit", y="product", orientation="h",
        color="margin_pct",
        color_continuous_scale="Purpor",
        labels={"profit": "Profit (₹)", "product": "", "margin_pct": "Margin %"},
        template="plotly_dark",
    )
    fig_prod.update_layout(
        plot_bgcolor="#1e293b", paper_bgcolor="#1e293b",
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(gridcolor="#334155"),
        yaxis=dict(gridcolor="#334155"),
        coloraxis_colorbar=dict(title="Margin %"),
    )
    st.plotly_chart(fig_prod, use_container_width=True)

with col_right:
    st.markdown("### 📊 Revenue vs Cost vs Profit")
    top10 = profit_df.nlargest(10, "revenue")
    fig_grouped = go.Figure()
    fig_grouped.add_trace(go.Bar(name="Revenue", x=top10["product"], y=top10["revenue"],
                                  marker_color="#6366f1"))
    fig_grouped.add_trace(go.Bar(name="Cost", x=top10["product"], y=top10["cost"],
                                  marker_color="#f59e0b"))
    fig_grouped.add_trace(go.Bar(name="Profit", x=top10["product"], y=top10["profit"],
                                  marker_color="#10b981"))
    fig_grouped.update_layout(
        barmode="group", template="plotly_dark",
        plot_bgcolor="#1e293b", paper_bgcolor="#1e293b",
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(gridcolor="#334155"),
        yaxis=dict(gridcolor="#334155", title="Amount (₹)"),
        legend=dict(font=dict(color="#e2e8f0")),
    )
    st.plotly_chart(fig_grouped, use_container_width=True)

# ── Period trend ────────────────────────────────────────────────────────────────
st.markdown(f"### 📅 Daily Profit Trend — Last {days_opt} Days")
if not period_df.empty:
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=period_df["sale_day"], y=period_df["daily_profit"],
        mode="lines+markers", name="Profit",
        line=dict(color="#10b981", width=3),
        fill="tozeroy", fillcolor="rgba(16,185,129,0.15)",
    ))
    fig_trend.add_trace(go.Scatter(
        x=period_df["sale_day"], y=period_df["daily_revenue"],
        mode="lines+markers", name="Revenue",
        line=dict(color="#6366f1", width=2, dash="dot"),
    ))
    fig_trend.update_layout(
        template="plotly_dark",
        plot_bgcolor="#1e293b", paper_bgcolor="#1e293b",
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(gridcolor="#334155"),
        yaxis=dict(gridcolor="#334155", title="Amount (₹)"),
        legend=dict(font=dict(color="#e2e8f0")),
    )
    st.plotly_chart(fig_trend, use_container_width=True)
else:
    warn(f"No sales in the last {days_opt} days.")

st.divider()

# ── Top 5 / Bottom 5 ────────────────────────────────────────────────────────────
col_top, col_bot = st.columns(2)

with col_top:
    st.markdown("### 🏆 Top 5 by Profit")
    top5 = profit_df.nlargest(5, "profit")[["product", "units_sold", "revenue", "profit", "margin_pct"]]
    top5.columns = ["Product", "Units Sold", "Revenue (₹)", "Profit (₹)", "Margin %"]
    st.dataframe(top5, use_container_width=True, hide_index=True)

with col_bot:
    st.markdown("### ⚠️ Bottom 5 by Profit")
    bot5 = profit_df.nsmallest(5, "profit")[["product", "units_sold", "revenue", "profit", "margin_pct"]]
    bot5.columns = ["Product", "Units Sold", "Revenue (₹)", "Profit (₹)", "Margin %"]
    st.dataframe(bot5, use_container_width=True, hide_index=True)

st.divider()

# ── Full table ──────────────────────────────────────────────────────────────────
st.markdown("### 📋 Complete Profit Table")
display = profit_df.copy()
display.columns = ["Product", "Units Sold", "Revenue (₹)", "Cost (₹)", "Profit (₹)", "Margin %"]
st.dataframe(display, use_container_width=True, hide_index=True)

csv_bytes = profit_df.to_csv(index=False).encode()
st.download_button("⬇️ Export Profit CSV", csv_bytes, "profit_analysis.csv", "text/csv")
