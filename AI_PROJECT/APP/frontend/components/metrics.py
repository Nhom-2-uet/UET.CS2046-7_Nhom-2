import streamlit as st

from utils.formatting import format_vnd


def render_financial_metrics() -> None:
    """Render the existing dashboard summary metrics using mock values."""
    col1, col2, col3 = st.columns(3)
    col1.metric("Tổng thu nhập", format_vnd(5_000_000))
    col2.metric("Tổng chi tiêu", format_vnd(2_500_000))
    col3.metric("Số dư", format_vnd(2_500_000))
