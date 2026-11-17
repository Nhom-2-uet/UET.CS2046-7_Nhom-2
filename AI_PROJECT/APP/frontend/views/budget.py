from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.formatting import format_vnd


def render_budget() -> None:
    """Render the Budget page with a session-local monthly budget form."""
    st.header("Quản lý ngân sách")
    st.caption("Theo dõi ngân sách, chi tiêu theo danh mục và các khoản chi bắt buộc.")

    st.session_state.setdefault("budget_settings_mock", None)
    st.session_state.setdefault("budget_monthly_input", 0)
    st.session_state.setdefault("budget_payday_input", 1)
    current_month = date.today().strftime("%Y-%m")
    spending_mock = st.session_state.get("budget_spending_mock")
    if spending_mock is None or spending_mock["month"] != current_month:
        st.session_state["budget_spending_mock"] = {
            "month": current_month,
            "transactions": [
                {"description": "Khoản chi minh họa 1", "amount_vnd": 1_500_000},
                {"description": "Khoản chi minh họa 2", "amount_vnd": 1_200_000},
                {"description": "Khoản chi minh họa 3", "amount_vnd": 550_000},
            ],
        }
    category_spending_mock = st.session_state.get(
        "budget_category_spending_mock"
    )
    if category_spending_mock is None or category_spending_mock["month"] != current_month:
        st.session_state["budget_category_spending_mock"] = {
            "month": current_month,
            "categories": [
                {"category": "Ăn uống", "amount_vnd": 1_200_000},
                {"category": "Đi lại", "amount_vnd": 600_000},
                {"category": "Học tập", "amount_vnd": 800_000},
                {"category": "Giải trí", "amount_vnd": 400_000},
                {"category": "Khác", "amount_vnd": 250_000},
            ],
        }

    with st.container(border=True):
        st.subheader("Thiết lập ngân sách")
        with st.form("monthly_budget_settings_form"):
            monthly_budget_vnd = st.number_input(
                "Ngân sách tháng (VND)",
                min_value=0,
                step=100_000,
                key="budget_monthly_input",
            )
            payday = st.selectbox(
                "Ngày nhận tiền",
                options=list(range(1, 32)),
                format_func=lambda day: f"Ngày {day}",
                key="budget_payday_input",
            )
            submitted = st.form_submit_button("Lưu thiết lập")

        if submitted:
            if monthly_budget_vnd <= 0:
                st.error("Ngân sách tháng phải lớn hơn 0 VND.")
            else:
                st.session_state["budget_settings_mock"] = {
                    "monthly_budget_vnd": int(monthly_budget_vnd),
                    "payday": int(payday),
                }
                st.success("Đã lưu thiết lập ngân sách mẫu.")

        saved_settings = st.session_state["budget_settings_mock"]
        if saved_settings is None:
            st.info("Nhập ngân sách tháng và ngày nhận tiền, sau đó lưu thiết lập.")
        else:
            budget_col, payday_col = st.columns(2)
            budget_col.metric(
                "Ngân sách tháng", format_vnd(saved_settings["monthly_budget_vnd"])
            )
            payday_col.metric("Ngày nhận tiền", f"Ngày {saved_settings['payday']}")

    with st.container(border=True):
        st.subheader("Tổng quan ngân sách")
        if saved_settings is None:
            st.info("Hãy thiết lập ngân sách tháng trước để xem tổng quan.")
        else:
            monthly_budget_vnd = saved_settings["monthly_budget_vnd"]
            if monthly_budget_vnd <= 0:
                st.info("Hãy thiết lập ngân sách tháng lớn hơn 0 để xem tổng quan.")
            else:
                monthly_expenses = st.session_state["budget_spending_mock"][
                    "transactions"
                ]
                total_spent_vnd = sum(
                    item["amount_vnd"] for item in monthly_expenses
                )
                remaining_vnd = monthly_budget_vnd - total_spent_vnd
                used_percentage = total_spent_vnd / monthly_budget_vnd * 100

                budget_col, spent_col, remaining_col, usage_col = st.columns(4)
                budget_col.metric("Ngân sách tháng", format_vnd(monthly_budget_vnd))
                spent_col.metric("Đã chi trong tháng", format_vnd(total_spent_vnd))
                remaining_col.metric("Còn lại", format_vnd(remaining_vnd))
                usage_col.metric("Đã sử dụng", f"{used_percentage:.1f}%")

                st.progress(min(used_percentage / 100, 1.0))
                if used_percentage < 80:
                    st.success("Chi tiêu trong mức an toàn.")
                elif used_percentage < 100:
                    st.warning("Bạn sắp sử dụng hết ngân sách tháng.")
                else:
                    st.error("Bạn đã dùng hết hoặc vượt ngân sách tháng.")

    with st.container(border=True):
        st.subheader("Chi tiêu theo danh mục")
        category_data = pd.DataFrame(
            st.session_state["budget_category_spending_mock"]["categories"]
        )
        total_category_spending = int(category_data["amount_vnd"].sum())
        category_data["percentage"] = (
            category_data["amount_vnd"] / total_category_spending * 100
        )
        highest_spending = category_data.loc[
            category_data["amount_vnd"].idxmax()
        ]

        highest_col, total_col = st.columns(2)
        highest_col.metric(
            f"Chi tiêu cao nhất · {highest_spending['category']}",
            format_vnd(int(highest_spending["amount_vnd"])),
        )
        total_col.metric(
            "Tổng chi tiêu theo danh mục",
            format_vnd(total_category_spending),
        )

        chart_col, table_col = st.columns(2)
        with chart_col:
            pie_chart = px.pie(
                category_data,
                names="category",
                values="amount_vnd",
                title="Tỷ trọng chi tiêu theo danh mục",
                labels={"category": "Danh mục", "amount_vnd": "Số tiền"},
            )
            pie_chart.update_traces(textinfo="label+percent")
            st.plotly_chart(pie_chart, use_container_width=True)

        with table_col:
            category_table = pd.DataFrame(
                {
                    "Danh mục": category_data["category"],
                    "Số tiền": category_data["amount_vnd"].map(format_vnd),
                    "Tỷ lệ": category_data["percentage"].map(
                        lambda percentage: f"{percentage:.1f}%"
                    ),
                }
            )
            st.dataframe(category_table, hide_index=True, use_container_width=True)

    with st.container(border=True):
        st.subheader("Khoản chi bắt buộc")
        st.info("Khu vực khoản chi bắt buộc sẽ được triển khai ở milestone tiếp theo.")
