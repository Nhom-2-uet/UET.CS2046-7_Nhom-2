from datetime import date, timedelta

import streamlit as st

from components.charts import render_dashboard_charts
from components.metrics import render_financial_metrics
from utils.formatting import format_date


def render_dashboard() -> None:
    """Render the dashboard with its current mock data and date filter."""
    st.header("Tổng quan tài chính")
    period = st.selectbox(
        "Chọn khoảng thời gian",
        ["Tháng này", "Tháng trước", "Tùy chỉnh"],
    )

    today = date.today()
    if period == "Tháng này":
        start_date = today.replace(day=1)
        end_date = today
    elif period == "Tháng trước":
        last_day_previous_month = today.replace(day=1) - timedelta(days=1)
        start_date = last_day_previous_month.replace(day=1)
        end_date = last_day_previous_month
    else:
        col_start, col_end = st.columns(2)
        with col_start:
            start_date = st.date_input("Từ ngày", value=today.replace(day=1))
        with col_end:
            end_date = st.date_input("Đến ngày", value=today)

    if start_date > end_date:
        st.error("Ngày bắt đầu không được sau ngày kết thúc.")
    else:
        st.info(
            f"Đang xem dữ liệu từ {format_date(start_date)} đến "
            f"{format_date(end_date)}"
        )

    st.divider()
    render_financial_metrics()
    st.divider()
    st.subheader("Phân tích thu chi")
    render_dashboard_charts()
    st.subheader("Chào mừng bạn đến với ứng dụng!")
    st.info("Đây là Dashboard đầu tiên của AI Expense Assistant.")
