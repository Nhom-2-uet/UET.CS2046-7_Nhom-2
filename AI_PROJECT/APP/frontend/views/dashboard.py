from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.api_client import request
from utils.formatting import format_date, format_vnd


def render_dashboard() -> None:
    st.header("Tổng quan tài chính")
    period = st.selectbox(
        "Chọn khoảng thời gian", ["Tháng này", "Tháng trước", "Tùy chỉnh"]
    )
    today = date.today()
    if period == "Tháng này":
        start = today.replace(day=1)
        end = today
    elif period == "Tháng trước":
        end = today.replace(day=1) - timedelta(days=1)
        start = end.replace(day=1)
    else:
        col_start, col_end = st.columns(2)
        start = col_start.date_input("Từ ngày", value=today.replace(day=1))
        end = col_end.date_input("Đến ngày", value=today)
    if start > end:
        st.error("Ngày bắt đầu không được sau ngày kết thúc.")
        return

    st.info(f"Đang xem dữ liệu từ {format_date(start)} đến {format_date(end)}")
    try:
        with st.spinner("Đang tổng hợp dữ liệu..."):
            result = request("finance.summary", {"start_date": start, "end_date": end})
    except Exception as error:
        st.error(f"Không tải được tổng quan tài chính: {error}")
        return

    summary = result["summary"]
    metrics = st.columns(3)
    metrics[0].metric("Tổng thu nhập", format_vnd(summary["total_income"]))
    metrics[1].metric("Tổng chi tiêu", format_vnd(summary["total_expense"]))
    metrics[2].metric("Số dư", format_vnd(summary["net_balance"]))

    records = result["transactions"]
    if not records:
        st.info("Chưa có giao dịch trong khoảng thời gian này.")
        return
    frame = pd.DataFrame([
        {
            "date": item.transaction_date,
            "type": item.transaction_type,
            "amount": item.amount_vnd,
            "category": item.category_name,
        }
        for item in records
    ])
    frame["Tuần"] = frame["date"].map(lambda value: f"Tuần {(value.day - 1) // 7 + 1}")
    weekly = (
        frame.pivot_table(index="Tuần", columns="type", values="amount", aggfunc="sum", fill_value=0)
        .reset_index()
    )
    weekly = weekly.rename(columns={"income": "Thu nhập", "expense": "Chi tiêu"})
    for column in ("Thu nhập", "Chi tiêu"):
        if column not in weekly:
            weekly[column] = 0
    charts = st.columns(2)
    with charts[0]:
        st.subheader("Thu nhập và chi tiêu theo tuần")
        fig = px.bar(weekly, x="Tuần", y=["Thu nhập", "Chi tiêu"], barmode="group")
        st.plotly_chart(fig, use_container_width=True)
    with charts[1]:
        st.subheader("Cơ cấu chi tiêu")
        category_data = pd.DataFrame(result["categories"]["categories"])
        if category_data.empty:
            st.info("Chưa có khoản chi trong giai đoạn này.")
        else:
            category_data = category_data.rename(columns={"amount": "Số tiền"})
            st.plotly_chart(
                px.pie(category_data, names="category", values="Số tiền"),
                use_container_width=True,
            )
