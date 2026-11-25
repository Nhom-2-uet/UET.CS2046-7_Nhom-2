from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.api_client import request
from utils.formatting import format_date, format_vnd


EXPENSE_STATUS_LABELS = {
    "unpaid": "Chưa thanh toán",
    "paid": "Đã thanh toán",
    "cancelled": "Đã hủy",
}


def render_budget() -> None:
    st.header("Quản lý ngân sách")
    st.caption("Thiết lập và theo dõi ngân sách, khoản chi bắt buộc từ database.")

    try:
        with st.spinner("Đang tải ngân sách..."):
            settings = request("budget.get")
            all_expenses = request("expense.list")
            transactions = request("transaction.list")
    except Exception as error:
        st.error(f"Không tải được dữ liệu ngân sách: {error}")
        return

    current = settings
    with st.container(border=True):
        st.subheader("Thiết lập ngân sách tháng")
        with st.form("monthly_budget_settings_form"):
            monthly_budget = st.number_input(
                "Ngân sách tháng (VND)", min_value=1, step=100_000,
                value=max(1, int(current.monthly_budget_vnd)) if current else 1,
            )
            weekday_limit = st.number_input(
                "Hạn mức mỗi ngày thường (VND, 0 = không đặt)", min_value=0, step=10_000,
                value=int(current.weekday_daily_limit_vnd) if current else 0,
            )
            weekend_limit = st.number_input(
                "Hạn mức mỗi ngày cuối tuần (VND, 0 = không đặt)", min_value=0, step=10_000,
                value=int(current.weekend_daily_limit_vnd) if current else 0,
            )
            payday = st.selectbox(
                "Ngày nhận tiền", list(range(1, 32)),
                index=(current.payday or 1) - 1 if current else 0,
                format_func=lambda day: f"Ngày {day}",
            )
            submitted = st.form_submit_button("Lưu thiết lập")
        if submitted:
            if monthly_budget <= 0:
                st.error("Ngân sách tháng phải lớn hơn 0 VND.")
            else:
                try:
                    with st.spinner("Đang lưu thiết lập..."):
                        settings = request(
                            "budget.save",
                            {
                                "monthly_budget_vnd": int(monthly_budget),
                                "weekday_daily_limit_vnd": int(weekday_limit),
                                "weekend_daily_limit_vnd": int(weekend_limit),
                                "payday": int(payday),
                            },
                        )
                    st.success("Đã lưu thiết lập ngân sách.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Không thể lưu ngân sách: {error}")
        if settings:
            st.metric("Ngân sách tháng", format_vnd(settings.monthly_budget_vnd))

    if not settings:
        st.info("Hãy lưu thiết lập ngân sách để xem tổng quan.")
    else:
        today = date.today()
        today_limit = (
            settings.weekend_daily_limit_vnd if today.weekday() >= 5
            else settings.weekday_daily_limit_vnd
        )
        today_spending = sum(
            row.amount_vnd for row in transactions
            if row.transaction_type == "expense" and row.transaction_date == today
        )
        st.subheader("Hạn mức chi tiêu hôm nay")
        if today_limit > 0:
            st.metric("Hạn mức hôm nay", format_vnd(today_limit))
            st.metric("Đã chi hôm nay", format_vnd(today_spending),
                      delta=f"Còn {format_vnd(today_limit - today_spending)}")
            daily_usage = today_spending / today_limit
            st.progress(min(max(daily_usage, 0), 1))
            if daily_usage >= 1:
                st.error("Bạn đã chạm hoặc vượt hạn mức hôm nay.")
            elif daily_usage >= 0.8:
                st.warning("Bạn sắp chạm hạn mức hôm nay.")
        else:
            st.info("Hạn mức cho hôm nay chưa được đặt. Số 0 nghĩa là không đặt hạn mức.")
        with st.container(border=True):
            st.subheader("Cảnh báo chi bất thường · Bản demo")
            st.caption(
                "Minh họa cách gộp cảnh báo vượt hạn mức ngày với giao dịch tăng đột biến. "
                "Dữ liệu bên dưới là ví dụ, chưa được phân tích từ giao dịch thực tế."
            )
            demo_cols = st.columns(3)
            demo_cols[0].metric("Danh mục", "Ăn uống")
            demo_cols[1].metric("Giao dịch minh họa", format_vnd(300_000))
            demo_cols[2].metric("So với mức thường", "3×")
            st.warning(
                "Ví dụ: khoản ăn uống 300.000 VND cao gấp 3 lần mức thường. "
                "Khi triển khai thật, cảnh báo sẽ dựa trên giao dịch và hạn mức đã lưu."
            )
        monthly_spending = sum(
            row.amount_vnd for row in transactions
            if row.transaction_type == "expense"
            and row.transaction_date.year == today.year
            and row.transaction_date.month == today.month
        )
        budget_amount = int(settings.monthly_budget_vnd)
        remaining = budget_amount - monthly_spending
        usage = monthly_spending / budget_amount if budget_amount else 0
        cols = st.columns(4)
        cols[0].metric("Ngân sách", format_vnd(budget_amount))
        cols[1].metric("Đã chi tháng này", format_vnd(monthly_spending))
        cols[2].metric("Còn lại", format_vnd(remaining))
        cols[3].metric("Đã sử dụng", f"{usage * 100:.1f}%")
        st.progress(min(max(usage, 0), 1))
        if usage >= 1:
            st.error("Bạn đã dùng hết hoặc vượt ngân sách tháng.")
        elif usage >= 0.8:
            st.warning("Bạn sắp sử dụng hết ngân sách tháng.")
        else:
            st.success("Chi tiêu đang trong mức ngân sách.")

    st.subheader("Chi tiêu theo danh mục tháng này")
    today = date.today()
    category_totals: dict[str, int] = {}
    for row in transactions:
        if (row.transaction_type == "expense" and row.transaction_date.year == today.year
                and row.transaction_date.month == today.month):
            category_totals[row.category_name] = (
                category_totals.get(row.category_name, 0) + row.amount_vnd
            )
    if category_totals:
        category_frame = pd.DataFrame(
            [{"Danh mục": name, "Số tiền": amount} for name, amount in category_totals.items()]
        )
        chart_col, table_col = st.columns(2)
        chart_col.plotly_chart(
            px.pie(category_frame, names="Danh mục", values="Số tiền"),
            use_container_width=True,
        )
        table_col.dataframe(
            category_frame.assign(**{"Số tiền": category_frame["Số tiền"].map(format_vnd)}),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("Chưa có giao dịch chi tiêu trong tháng này.")

    st.subheader("Khoản chi bắt buộc")
    with st.expander("Thêm khoản chi", expanded=False):
        with st.form("required_expense_create_form", clear_on_submit=True):
            name = st.text_input("Tên khoản chi", max_chars=150)
            amount = st.number_input("Số tiền (VND)", min_value=1, step=10_000)
            due_date = st.date_input("Ngày đến hạn", value=date.today())
            add = st.form_submit_button("Thêm khoản chi")
        if add:
            if amount <= 0:
                st.error("Số tiền khoản chi phải lớn hơn 0 VND.")
            else:
                try:
                    with st.spinner("Đang thêm khoản chi..."):
                        request("expense.create", {
                            "name": name, "amount_vnd": int(amount), "due_date": due_date
                        })
                    st.success("Đã thêm khoản chi bắt buộc.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Không thể thêm khoản chi: {error}")

    status_filter = st.selectbox(
        "Lọc trạng thái", ["Tất cả", *EXPENSE_STATUS_LABELS.values()]
    )
    status_by_label = {value: key for key, value in EXPENSE_STATUS_LABELS.items()}
    visible_expenses = [
        item for item in all_expenses
        if status_filter == "Tất cả" or item.status == status_by_label[status_filter]
    ]
    if not visible_expenses:
        st.info("Không có khoản chi nào phù hợp.")
    else:
        table = pd.DataFrame([
            {
                "ID": item.expense_id,
                "Tên khoản chi": item.name,
                "Số tiền": format_vnd(item.amount_vnd),
                "Ngày đến hạn": format_date(item.due_date),
                "Trạng thái": EXPENSE_STATUS_LABELS[item.status],
            }
            for item in visible_expenses
        ])
        st.dataframe(table, hide_index=True, use_container_width=True)
        editable = [item for item in visible_expenses if item.status == "unpaid"]
        if editable:
            chosen = st.selectbox(
                "Chọn khoản chưa thanh toán",
                editable,
                format_func=lambda item: f"{item.name} · {format_vnd(item.amount_vnd)}",
            )
            with st.expander("Sửa khoản chi"):
                with st.form(f"expense_edit_{chosen.expense_id}"):
                    edit_name = st.text_input("Tên khoản chi", value=chosen.name)
                    edit_amount = st.number_input(
                        "Số tiền (VND)", min_value=1, value=int(chosen.amount_vnd), step=10_000
                    )
                    edit_due = st.date_input("Ngày đến hạn", value=chosen.due_date)
                    save = st.form_submit_button("Lưu thay đổi")
                if save:
                    if edit_amount <= 0:
                        st.error("Số tiền khoản chi phải lớn hơn 0 VND.")
                    else:
                        try:
                            updated = request("expense.update", {
                                "expense_id": chosen.expense_id,
                                "name": edit_name,
                                "amount_vnd": int(edit_amount),
                                "due_date": edit_due,
                            })
                            if updated is None:
                                st.error("Khoản chi không còn ở trạng thái có thể sửa.")
                            else:
                                st.success("Đã cập nhật khoản chi.")
                                st.rerun()
                        except Exception as error:
                            st.error(f"Không thể cập nhật khoản chi: {error}")
            if st.button("Xóa khoản chi", key=f"expense_delete_{chosen.expense_id}"):
                try:
                    deleted = request("expense.delete", {"expense_id": chosen.expense_id})
                    if deleted:
                        st.success("Đã xóa khoản chi.")
                        st.rerun()
                    else:
                        st.error("Chỉ có thể xóa khoản chi chưa thanh toán.")
                except Exception as error:
                    st.error(f"Không thể xóa khoản chi: {error}")
