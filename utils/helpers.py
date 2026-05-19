"""
utils/helpers.py — Shared UI helpers for Streamlit pages
"""
import streamlit as st


CURRENCY = "₹"


def fmt_currency(value) -> str:
    try:
        return f"{CURRENCY}{float(value):,.2f}"
    except Exception:
        return f"{CURRENCY}0.00"


def fmt_pct(value) -> str:
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "—"


def stock_badge(status: str) -> str:
    badges = {
        "Out of Stock": "🔴 Out of Stock",
        "Low Stock":    "🟡 Low Stock",
        "OK":           "🟢 OK",
    }
    return badges.get(status, status)


def metric_card(label: str, value: str, delta: str = "", icon: str = "") -> None:
    """Render a styled metric inside a colored container."""
    st.metric(label=f"{icon} {label}" if icon else label, value=value, delta=delta or None)


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(f"## {title}")
    if subtitle:
        st.markdown(f"<p style='color:#9ca3af;margin-top:-12px'>{subtitle}</p>",
                    unsafe_allow_html=True)
    st.divider()


def success(msg: str) -> None:
    st.success(f"✅ {msg}")


def error(msg: str) -> None:
    st.error(f"❌ {msg}")


def warn(msg: str) -> None:
    st.warning(f"⚠️ {msg}")
