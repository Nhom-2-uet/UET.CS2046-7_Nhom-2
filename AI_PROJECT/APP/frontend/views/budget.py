from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.formatting import format_date, format_vnd


EXPENSE_STATUS_LABELS = {
    "unpaid": "Chưa thanh toán",
    "paid": "Đã thanh toán",
    "cancelled": "Đã hủy",
}


def _initial_required_expenses() -> list[dict]:
    today = date.today()
    return [
        {
            "expense_id": 1,
            "name": "Tiền trọ",
            "amount_vnd": 2_000_000,
            "due_date": today + timedelta(days=5),
            "status": "unpaid",
            "paid_transaction_id": None,
        },
        {
            "expense_id": 2,
            "name": "Tiền điện nước",
            "amount_vnd": 450_000,
            "due_date": today + timedelta(days=10),
            "status": "unpaid",
            "paid_transaction_id": None,
        },
        {
            "expense_id": 3,
            "name": "Internet",
            "amount_vnd": 200_000,
            "due_date": today + timedelta(days=12),
            "status": "unpaid",
            "paid_transaction_id": None,
        },
    ]


def render_budget() -> None:
    """Render the Budget page with a session-local monthly budget form."""
    st.header("Quản lý ngân sách")
    st.caption("Theo dõi ngân sách, chi tiêu theo danh mục và các khoản chi bắt buộc.")

    st.session_state.setdefault("budget_settings_mock", None)
    st.session_state.setdefault("budget_monthly_input", 0)
    st.session_state.setdefault("budget_payday_input", 1)
    if "budget_required_expenses_mock" not in st.session_state:
        st.session_state["budget_required_expenses_mock"] = (
            _initial_required_expenses()
        )
    st.session_state.setdefault(
        "budget_required_expense_next_id",
        max(
            (
                expense["expense_id"]
                for expense in st.session_state["budget_required_expenses_mock"]
            ),
            default=0,
        ) + 1,
    )
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
        required_expenses = st.session_state["budget_required_expenses_mock"]
        flash_message = st.session_state.pop(
            "budget_required_expenses_flash", None
        )
        if flash_message is not None:
            st.success(flash_message)

        active_expenses = [
            expense for expense in required_expenses
            if expense["status"] != "cancelled"
        ]
        unpaid_expenses = [
            expense for expense in required_expenses
            if expense["status"] == "unpaid"
        ]
        total_active_amount = sum(
            expense["amount_vnd"] for expense in active_expenses
        )
        total_unpaid_amount = sum(
            expense["amount_vnd"] for expense in unpaid_expenses
        )

        count_col, amount_col, unpaid_col = st.columns(3)
        count_col.metric("Tổng số khoản chi", len(required_expenses))
        amount_col.metric(
            "Tổng tiền (không gồm khoản đã hủy)",
            format_vnd(total_active_amount),
        )
        unpaid_col.metric("Tổng tiền chưa thanh toán", format_vnd(total_unpaid_amount))

        with st.expander("Thêm khoản chi bắt buộc", expanded=False):
            with st.form("add_required_expense_form", clear_on_submit=True):
                new_expense_name = st.text_input(
                    "Tên khoản chi", max_chars=150
                )
                new_expense_amount = st.number_input(
                    "Số tiền (VND)", min_value=0, step=10_000
                )
                new_expense_due_date = st.date_input(
                    "Ngày đến hạn", value=date.today()
                )
                add_expense_submitted = st.form_submit_button("Thêm khoản chi")

            if add_expense_submitted:
                if not new_expense_name.strip():
                    st.error("Vui lòng nhập tên khoản chi.")
                elif new_expense_amount <= 0:
                    st.error("Số tiền phải lớn hơn 0 VND.")
                else:
                    next_expense_id = st.session_state[
                        "budget_required_expense_next_id"
                    ]
                    st.session_state["budget_required_expense_next_id"] += 1
                    required_expenses.append(
                        {
                            "expense_id": next_expense_id,
                            "name": new_expense_name.strip(),
                            "amount_vnd": int(new_expense_amount),
                            "due_date": new_expense_due_date,
                            "status": "unpaid",
                            "paid_transaction_id": None,
                        }
                    )
                    st.session_state["budget_required_expenses_mock"] = (
                        required_expenses
                    )
                    st.session_state["budget_required_expenses_flash"] = (
                        "Đã thêm khoản chi bắt buộc."
                    )
                    st.rerun()

        filter_options = {
            "Tất cả": None,
            "Chưa thanh toán": "unpaid",
            "Đã thanh toán": "paid",
            "Đã hủy": "cancelled",
        }
        selected_status_label = st.selectbox(
            "Lọc theo trạng thái",
            list(filter_options),
            key="required_expense_status_filter",
        )
        selected_status = filter_options[selected_status_label]
        filtered_expenses = [
            expense for expense in required_expenses
            if selected_status is None or expense["status"] == selected_status
        ]

        if filtered_expenses:
            expense_table = pd.DataFrame(
                [
                    {
                        "Tên khoản chi": expense["name"],
                        "Số tiền (VND)": format_vnd(expense["amount_vnd"]),
                        "Ngày đến hạn": format_date(expense["due_date"]),
                        "Trạng thái": EXPENSE_STATUS_LABELS[expense["status"]],
                        "Thao tác": (
                            "Sửa / Xóa"
                            if expense["status"] == "unpaid"
                            else "Chỉ xem"
                        ),
                    }
                    for expense in filtered_expenses
                ]
            )
            st.dataframe(expense_table, hide_index=True, use_container_width=True)
        else:
            st.info("Không có khoản chi nào phù hợp với trạng thái đã chọn.")

        editable_expenses = [
            expense for expense in filtered_expenses
            if expense["status"] == "unpaid"
        ]
        if editable_expenses:
            with st.expander("Chỉnh sửa hoặc xóa khoản chưa thanh toán"):
                editable_ids = [
                    expense["expense_id"] for expense in editable_expenses
                ]
                selected_expense_id = st.selectbox(
                    "Chọn khoản chi",
                    editable_ids,
                    format_func=lambda expense_id: next(
                        expense["name"]
                        for expense in editable_expenses
                        if expense["expense_id"] == expense_id
                    ),
                    key=(
                        "required_expense_action_"
                        + "_".join(map(str, editable_ids))
                    ),
                )
                selected_expense = next(
                    expense for expense in editable_expenses
                    if expense["expense_id"] == selected_expense_id
                )

                with st.form(f"edit_required_expense_{selected_expense_id}"):
                    edited_name = st.text_input(
                        "Tên khoản chi",
                        value=selected_expense["name"],
                        max_chars=150,
                    )
                    edited_amount = st.number_input(
                        "Số tiền (VND)",
                        min_value=0,
                        value=int(selected_expense["amount_vnd"]),
                        step=10_000,
                    )
                    edited_due_date = st.date_input(
                        "Ngày đến hạn",
                        value=selected_expense["due_date"],
                    )
                    edit_submitted = st.form_submit_button("Lưu thay đổi")

                if edit_submitted:
                    if not edited_name.strip():
                        st.error("Tên khoản chi không được để trống.")
                    elif edited_amount <= 0:
                        st.error("Số tiền phải lớn hơn 0 VND.")
                    else:
                        selected_expense["name"] = edited_name.strip()
                        selected_expense["amount_vnd"] = int(edited_amount)
                        selected_expense["due_date"] = edited_due_date
                        st.session_state["budget_required_expenses_mock"] = (
                            required_expenses
                        )
                        st.session_state["budget_required_expenses_flash"] = (
                            "Đã cập nhật khoản chi."
                        )
                        st.rerun()

                if st.button(
                    "Xóa khoản chi",
                    key=f"delete_required_expense_{selected_expense_id}",
                    type="secondary",
                ):
                    st.session_state["budget_required_expenses_mock"] = [
                        expense for expense in required_expenses
                        if expense["expense_id"] != selected_expense_id
                    ]
                    st.session_state["budget_required_expenses_flash"] = (
                        "Đã xóa khoản chi."
                    )
                    st.rerun()
