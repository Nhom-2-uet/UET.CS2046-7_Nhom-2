"""Budget overview and existing budget/required-expense workflows."""

from datetime import date, timedelta
from html import escape
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.api_client import request
from frontend.components.design_system import (
    render_empty_state,
    render_error_state,
    render_page_header,
    section_container,
)
from utils.formatting import format_date, format_vnd


EXPENSE_STATUS_LABELS = {
    "unpaid": "Chưa thanh toán",
    "paid": "Đã thanh toán",
    "cancelled": "Đã hủy",
}

_BUDGET_STYLES = """
<style>
.budget-period-note { color: #8491a3; font-size: .88rem; margin: -.2rem 0 1rem; }
.budget-section-title { margin: 1.55rem 0 .18rem; color: #202938; font-size: 1.1rem; font-weight: 700; }
.budget-section-caption { margin: 0 0 .8rem; color: #8491a3; font-size: .86rem; }
.budget-status { display: inline-block; border-radius: 999px; padding: .22rem .65rem; font-size: .77rem; font-weight: 650; }
.budget-status-ok { background: #e8f7ef; color: #168451; }
.budget-status-warning { background: #fff3e4; color: #bd6900; }
.budget-status-danger { background: #fff0ef; color: #cf3e37; }
.budget-status-neutral { background: #eef2f7; color: #64748b; }
.budget-expense-total { color: #d96516; background: #fff3e6; border-radius: 999px; padding: .3rem .7rem; font-size: .8rem; font-weight: 700; text-align: center; }
[data-testid="stMetricLabel"] p { color: #8491a3; font-size: .82rem; font-weight: 600; }
[data-testid="stMetricValue"] { color: #202938; font-size: clamp(1.2rem, 2vw, 1.65rem); }
@media (max-width: 700px) {
    .budget-section-title { margin-top: 1.15rem; }
    [data-testid="stMetricValue"] { font-size: 1.15rem; }
}
</style>
"""


def _month_shift(value: date, offset: int) -> date:
    month_index = value.year * 12 + value.month - 1 + offset
    year, month_index = divmod(month_index, 12)
    return date(year, month_index + 1, 1)


def _shift_selected_month(offset: int) -> None:
    selected = st.session_state.get("budget_month", date.today().replace(day=1))
    st.session_state["budget_month"] = _month_shift(selected, offset)


def _toggle_settings() -> None:
    st.session_state["budget_settings_open"] = not st.session_state.get(
        "budget_settings_open", False
    )


def _amount(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if parsed >= 0 else None


def _status_view(usage: float | None) -> tuple[str, str, str]:
    if usage is None:
        return "Chưa thiết lập ngân sách", "budget-status-neutral", "Chưa có hạn mức tháng"
    if usage >= 1:
        return "Đã vượt ngân sách", "budget-status-danger", "Chi tiêu đã vượt hạn mức"
    if usage >= 0.8:
        return "Sắp chạm hạn mức", "budget-status-warning", "Chi tiêu đang gần hạn mức"
    return "Trong ngân sách", "budget-status-ok", "Chi tiêu đang trong mức cho phép"


def _transaction_values(
    transactions: list[Any],
) -> tuple[int, list[dict[str, Any]], int]:
    """Normalize actual expense transactions for monthly totals and charts."""
    rows: list[dict[str, Any]] = []
    skipped = 0
    for item in transactions:
        transaction_type = getattr(item, "transaction_type", None)
        transaction_date = getattr(item, "transaction_date", None)
        amount = _amount(getattr(item, "amount_vnd", None))
        if transaction_type == "income":
            continue
        if transaction_type != "expense" or amount is None or not isinstance(transaction_date, date):
            skipped += 1
            continue
        rows.append(
            {
                "date": transaction_date,
                "amount": amount,
                "category": getattr(item, "category_name", None),
            }
        )
    return sum(row["amount"] for row in rows), rows, skipped


def _render_settings(settings: Any) -> None:
    """Render existing monthly and daily limit settings without changing payloads."""
    current_monthly = _amount(getattr(settings, "monthly_budget_vnd", 0)) or 0
    current_weekday = _amount(getattr(settings, "weekday_daily_limit_vnd", 0)) or 0
    current_weekend = _amount(getattr(settings, "weekend_daily_limit_vnd", 0)) or 0
    current_payday = getattr(settings, "payday", None)

    with st.expander(
        "Thiết lập ngân sách",
        expanded=st.session_state.get("budget_settings_open", False),
    ):
        st.caption(
            "Các thiết lập hiện được backend hỗ trợ: ngân sách tháng, hạn mức ngày thường/cuối tuần và ngày nhận tiền."
        )
        with st.form("monthly_budget_settings_form"):
            monthly_budget = st.number_input(
                "Ngân sách tháng (VND · 0 = chưa đặt)",
                min_value=0,
                step=100_000,
                value=current_monthly,
            )
            weekday_limit = st.number_input(
                "Hạn mức ngày thường (VND · 0 = không giới hạn)",
                min_value=0,
                step=10_000,
                value=current_weekday,
            )
            weekend_limit = st.number_input(
                "Hạn mức cuối tuần (VND · 0 = không giới hạn)",
                min_value=0,
                step=10_000,
                value=current_weekend,
            )
            payday_options = [None, *range(1, 32)]
            payday = st.selectbox(
                "Ngày nhận tiền",
                payday_options,
                index=payday_options.index(current_payday)
                if current_payday in payday_options
                else 0,
                format_func=lambda value: "Chưa thiết lập" if value is None else f"Ngày {value}",
            )
            submitted = st.form_submit_button(
                "Lưu thiết lập", type="primary", use_container_width=True
            )

        if submitted:
            values = (monthly_budget, weekday_limit, weekend_limit)
            if any(value < 0 for value in values):
                render_error_state("Các hạn mức phải là số tiền không âm.")
            else:
                try:
                    with st.spinner("Đang lưu thiết lập..."):
                        request(
                            "budget.save",
                            {
                                "monthly_budget_vnd": int(monthly_budget),
                                "weekday_daily_limit_vnd": int(weekday_limit),
                                "weekend_daily_limit_vnd": int(weekend_limit),
                                "payday": int(payday) if payday is not None else None,
                            },
                        )
                    st.session_state["budget_settings_open"] = False
                    st.success("Đã lưu thiết lập ngân sách.")
                    st.rerun()
                except Exception as error:
                    render_error_state(f"Không thể lưu ngân sách: {error}")


def _render_required_expenses(all_expenses: list[Any]) -> None:
    st.markdown(
        '<div class="budget-section-title">Khoản chi bắt buộc</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="budget-section-caption">Các khoản cần thanh toán và ngày đến hạn.</div>',
        unsafe_allow_html=True,
    )

    valid_expenses = [
        item
        for item in all_expenses
        if getattr(item, "status", None) in EXPENSE_STATUS_LABELS
    ]
    if len(valid_expenses) < len(all_expenses):
        st.warning("Một số khoản chi bị ẩn vì dữ liệu trạng thái không hợp lệ hoặc còn thiếu.")
    unpaid_total = sum(
        _amount(getattr(item, "amount_vnd", None)) or 0
        for item in valid_expenses
        if item.status == "unpaid"
    )
    header, total_col, expand_col = st.columns([4, 1.5, 1])
    with header:
        st.markdown("**🗓️  Khoản chi bắt buộc**")
    with total_col:
        st.markdown(
            f'<div class="budget-expense-total">Chưa thanh toán: {format_vnd(unpaid_total)}</div>',
            unsafe_allow_html=True,
        )
    with expand_col:
        add_open = st.button("＋ Thêm khoản chi", key="required_expense_add_open")

    if add_open:
        st.session_state["required_expense_create_open"] = not st.session_state.get(
            "required_expense_create_open", False
        )
    if st.session_state.get("required_expense_create_open", False):
        with section_container():
            st.markdown("**Thêm khoản chi**")
            with st.form("required_expense_create_form", clear_on_submit=True):
                name = st.text_input("Tên khoản chi", max_chars=150)
                amount = st.number_input("Số tiền (VND)", min_value=1, step=10_000)
                due_date = st.date_input("Ngày đến hạn", value=date.today())
                add = st.form_submit_button("Tạo khoản chi", type="primary")
            if add:
                if not name.strip() or amount <= 0:
                    render_error_state("Vui lòng nhập tên khoản chi và số tiền lớn hơn 0.")
                else:
                    try:
                        with st.spinner("Đang thêm khoản chi..."):
                            request(
                                "expense.create",
                                {"name": name.strip(), "amount_vnd": int(amount), "due_date": due_date},
                            )
                        st.session_state["required_expense_create_open"] = False
                        st.success("Đã thêm khoản chi bắt buộc.")
                        st.rerun()
                    except Exception as error:
                        render_error_state(f"Không thể thêm khoản chi: {error}")

    if not valid_expenses:
        render_empty_state("Chưa có khoản chi bắt buộc.")
        return

    status_filter = st.selectbox(
        "Trạng thái khoản chi",
        ["Tất cả", *EXPENSE_STATUS_LABELS.values()],
        label_visibility="collapsed",
        key="required_expense_status_filter",
    )
    status_by_label = {label: status for status, label in EXPENSE_STATUS_LABELS.items()}
    visible_expenses = [
        item
        for item in valid_expenses
        if status_filter == "Tất cả" or item.status == status_by_label[status_filter]
    ]
    if not visible_expenses:
        render_empty_state("Không có khoản chi phù hợp với trạng thái đã chọn.")
        return

    for item in visible_expenses:
        due_date = getattr(item, "due_date", None)
        due_label = format_date(due_date) if isinstance(due_date, date) else "Chưa có ngày"
        amount = _amount(getattr(item, "amount_vnd", None))
        amount_label = format_vnd(amount) if amount is not None else "Số tiền chưa rõ"
        name = escape(str(getattr(item, "name", "Khoản chi")))
        status = item.status
        with st.expander(f"📅  {name}  ·  {amount_label}  ·  {EXPENSE_STATUS_LABELS[status]}"):
            detail_cols = st.columns([1, 1, 1.5])
            detail_cols[0].caption("Ngày đến hạn")
            detail_cols[0].write(due_label)
            detail_cols[1].caption("Số tiền")
            detail_cols[1].write(amount_label)
            detail_cols[2].caption("Trạng thái")
            detail_cols[2].write(EXPENSE_STATUS_LABELS[status])
            paid_transaction_id = getattr(item, "paid_transaction_id", None)
            if paid_transaction_id:
                st.caption(f"Đã liên kết với giao dịch #{paid_transaction_id}.")
            if status != "unpaid":
                st.caption("Chỉ khoản chưa thanh toán mới có thể chỉnh sửa hoặc xóa.")
                continue

            edit_col, delete_col = st.columns([2, 1])
            with edit_col:
                with st.form(f"expense_edit_{item.expense_id}"):
                    edit_name = st.text_input(
                        "Tên khoản chi", value=getattr(item, "name", ""),
                        key=f"expense_name_{item.expense_id}",
                    )
                    edit_amount = st.number_input(
                        "Số tiền (VND)", min_value=1,
                        value=max(1, amount or 1), step=10_000,
                        key=f"expense_amount_{item.expense_id}",
                    )
                    edit_due = st.date_input(
                        "Ngày đến hạn", value=due_date if isinstance(due_date, date) else date.today(),
                        key=f"expense_due_{item.expense_id}",
                    )
                    save = st.form_submit_button("Lưu thay đổi")
                if save:
                    if not edit_name.strip() or edit_amount <= 0:
                        render_error_state("Vui lòng nhập tên khoản chi và số tiền lớn hơn 0.")
                    else:
                        try:
                            updated = request(
                                "expense.update",
                                {
                                    "expense_id": item.expense_id,
                                    "name": edit_name.strip(),
                                    "amount_vnd": int(edit_amount),
                                    "due_date": edit_due,
                                },
                            )
                            if updated is None:
                                render_error_state("Khoản chi không còn ở trạng thái có thể sửa.")
                            else:
                                st.success("Đã cập nhật khoản chi.")
                                st.rerun()
                        except Exception as error:
                            render_error_state(f"Không thể cập nhật khoản chi: {error}")
            with delete_col:
                if st.button(
                    "Xóa khoản chi",
                    key=f"expense_delete_{item.expense_id}",
                    type="secondary",
                    use_container_width=True,
                ):
                    try:
                        deleted = request("expense.delete", {"expense_id": item.expense_id})
                        if deleted:
                            st.success("Đã xóa khoản chi.")
                            st.rerun()
                        else:
                            render_error_state("Chỉ có thể xóa khoản chi chưa thanh toán.")
                    except Exception as error:
                        render_error_state(f"Không thể xóa khoản chi: {error}")


def render_budget() -> None:
    st.markdown(_BUDGET_STYLES, unsafe_allow_html=True)

    if "budget_month" not in st.session_state:
        st.session_state["budget_month"] = date.today().replace(day=1)
    if "budget_settings_open" not in st.session_state:
        st.session_state["budget_settings_open"] = False

    heading, controls = st.columns([2.2, 1.8])
    with heading:
        render_page_header(
            "Ngân sách",
            "Theo dõi chi tiêu và lên kế hoạch tài chính theo tháng.",
        )
    with controls:
        previous_col, month_col, next_col = st.columns([1, 3, 1])
        previous_col.button("‹", help="Tháng trước", on_click=_shift_selected_month, args=(-1,))
        now = date.today().replace(day=1)
        month_options = [_month_shift(now, offset) for offset in range(-24, 13)]
        selected_month = month_col.selectbox(
            "Tháng",
            month_options,
            key="budget_month",
            format_func=lambda value: f"Tháng {value.month:02d}/{value.year}",
            label_visibility="collapsed",
        )
        next_col.button("›", help="Tháng tiếp theo", on_click=_shift_selected_month, args=(1,))
        st.button(
            "⚙  Thiết lập ngân sách",
            on_click=_toggle_settings,
            type="primary",
            use_container_width=True,
        )

    period_start = selected_month
    period_end = _month_shift(selected_month, 1) - timedelta(days=1)
    st.markdown(
        f'<div class="budget-period-note">Tổng hợp giao dịch từ {format_date(period_start)} đến {format_date(period_end)}</div>',
        unsafe_allow_html=True,
    )

    errors: dict[str, Exception] = {}
    settings = None
    all_expenses: list[Any] = []
    transactions: list[Any] = []
    categories: list[Any] = []
    with st.spinner("Đang tải dữ liệu ngân sách..."):
        try:
            settings = request("budget.get")
        except Exception as error:
            errors["settings"] = error
        try:
            all_expenses = request("expense.list") or []
            if not isinstance(all_expenses, list):
                all_expenses = []
                raise TypeError("API expense.list không trả về danh sách.")
        except Exception as error:
            errors["expenses"] = error
        try:
            transactions = request(
                "transaction.list",
                {"start_date": period_start, "end_date": period_end},
            ) or []
            if not isinstance(transactions, list):
                transactions = []
                raise TypeError("API transaction.list không trả về danh sách.")
        except Exception as error:
            errors["transactions"] = error
        try:
            categories = request("transaction.categories", {"transaction_type": "expense"}) or []
            if not isinstance(categories, list):
                categories = []
                raise TypeError("API transaction.categories không trả về danh sách.")
        except Exception as error:
            errors["categories"] = error

    if "settings" in errors:
        render_error_state(f"Không tải được thiết lập ngân sách: {errors['settings']}")
    if "transactions" in errors:
        render_error_state(f"Không tải được giao dịch tháng này: {errors['transactions']}")
    if "expenses" in errors:
        render_error_state(f"Không tải được khoản chi bắt buộc: {errors['expenses']}")
    if "categories" in errors:
        st.caption(f"Không tải được danh mục chi tiêu: {errors['categories']}")

    if "settings" not in errors:
        _render_settings(settings)

    monthly_spending, expense_rows, skipped_transactions = _transaction_values(transactions)
    if skipped_transactions and "transactions" not in errors:
        st.warning(
            f"Đã bỏ qua {skipped_transactions} giao dịch chi thiếu ngày, loại hoặc số tiền hợp lệ."
        )
    configured_budget = _amount(getattr(settings, "monthly_budget_vnd", None)) if settings else None
    configured_budget = configured_budget if configured_budget and configured_budget > 0 else None
    remaining = configured_budget - monthly_spending if configured_budget is not None else None
    usage = monthly_spending / configured_budget if configured_budget is not None else None
    if "settings" in errors:
        status_label, status_class, status_message = (
            "Không tải được thiết lập", "budget-status-neutral", ""
        )
    elif "transactions" in errors:
        status_label, status_class, status_message = (
            "Không tải được giao dịch", "budget-status-neutral", ""
        )
    else:
        status_label, status_class, status_message = _status_view(usage)

    st.markdown(
        '<div class="budget-section-title">Tổng quan ngân sách tháng</div>',
        unsafe_allow_html=True,
    )
    if "settings" in errors:
        st.info("Chưa thể xác định trạng thái ngân sách vì không tải được thiết lập.")
    elif configured_budget is None:
        st.info("Chưa thiết lập ngân sách tháng. Mở phần thiết lập để nhập hạn mức của bạn.")
    overview_col, chart_col = st.columns([1.1, 1])
    with overview_col:
        with section_container():
            st.markdown("**▣  Tình hình ngân sách**")
            st.markdown(
                f'<span class="budget-status {status_class}">{status_label}</span>',
                unsafe_allow_html=True,
            )
            metrics = st.columns(3)
            metrics[0].metric(
                "Ngân sách tháng",
                (
                    format_vnd(configured_budget)
                    if configured_budget is not None
                    else "Lỗi tải" if "settings" in errors else "Chưa đặt"
                ),
            )
            metrics[1].metric(
                "Đã chi",
                format_vnd(monthly_spending) if "transactions" not in errors else "—",
            )
            metrics[2].metric(
                "Còn lại",
                format_vnd(remaining)
                if remaining is not None and "transactions" not in errors
                else "—",
            )
            if configured_budget is not None and "transactions" not in errors:
                progress = min(max(usage or 0, 0), 1)
                st.progress(progress, text=f"Đã sử dụng {usage * 100:.1f}%")
            if "transactions" in errors:
                st.caption("Chưa thể tính tỷ lệ sử dụng vì không tải được giao dịch.")
            else:
                st.caption(status_message)

            today = date.today()
            if settings and "transactions" not in errors and selected_month == today.replace(day=1):
                today_limit = _amount(
                    getattr(
                        settings,
                        "weekend_daily_limit_vnd" if today.weekday() >= 5 else "weekday_daily_limit_vnd",
                        0,
                    )
                ) or 0
                today_spending = sum(
                    row["amount"] for row in expense_rows if row["date"] == today
                )
                if today_limit > 0:
                    st.caption(
                        f"Hôm nay: {format_vnd(today_spending)} / {format_vnd(today_limit)}"
                    )
                    st.progress(min(today_spending / today_limit, 1.0))
                    if today_spending >= today_limit:
                        st.warning("Chi tiêu hôm nay đã chạm hoặc vượt hạn mức.")
                    elif today_spending / today_limit >= 0.8:
                        st.warning("Chi tiêu hôm nay đang gần hạn mức.")
                else:
                    st.caption("Chưa đặt hạn mức chi tiêu ngày cho hôm nay.")

    with chart_col:
        with section_container():
            st.markdown("**▥  Chi tiêu theo thời gian**")
            if "transactions" in errors:
                render_empty_state("Biểu đồ chưa khả dụng do không tải được giao dịch.")
            elif not expense_rows:
                render_empty_state("Chưa có giao dịch chi tiêu trong tháng đã chọn.")
            else:
                daily = (
                    pd.DataFrame(expense_rows)
                    .groupby("date", as_index=False)["amount"]
                    .sum()
                    .sort_values("date")
                )
                chart = px.bar(
                    daily,
                    x="date",
                    y="amount",
                    labels={"date": "Ngày", "amount": "Chi tiêu (VND)"},
                    color_discrete_sequence=["#3984E8"],
                )
                chart.update_layout(
                    height=275,
                    margin=dict(l=8, r=8, t=12, b=8),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                    font=dict(color="#64748b"),
                )
                chart.update_xaxes(showgrid=False, title=None)
                chart.update_yaxes(gridcolor="#e8edf4", zeroline=False)
                st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})

    if "expenses" not in errors:
        _render_required_expenses(all_expenses)
    else:
        st.markdown(
            '<div class="budget-section-title">Khoản chi bắt buộc</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="budget-section-title">Chi tiêu theo danh mục</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="budget-section-caption">Số liệu chi tiêu thật trong tháng; backend hiện chưa lưu hạn mức riêng cho từng danh mục.</div>',
        unsafe_allow_html=True,
    )
    category_totals: dict[str, int] = {}
    for row in expense_rows:
        category_name = row["category"]
        if isinstance(category_name, str) and category_name.strip():
            category_totals[category_name] = (
                category_totals.get(category_name, 0) + row["amount"]
            )
    known_names = {
        item.get("name")
        for item in categories
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    names = sorted(known_names | set(category_totals))
    total_spending = sum(category_totals.values())
    unassigned_spending = sum(
        row["amount"]
        for row in expense_rows
        if not isinstance(row["category"], str) or not row["category"].strip()
    )
    if "transactions" in errors:
        render_empty_state("Không thể hiển thị chi tiêu theo danh mục vì API giao dịch đang lỗi.")
    elif not names:
        render_empty_state("Chưa có danh mục chi tiêu hoặc giao dịch trong tháng này.")
    else:
        if unassigned_spending:
            st.caption(
                f"{format_vnd(unassigned_spending)} giao dịch thiếu tên danh mục nên không được gộp vào các mục bên dưới."
            )
        category_columns = st.columns(2)
        for index, name in enumerate(names):
            spent = category_totals.get(name, 0)
            share = spent / total_spending if total_spending else 0
            with category_columns[index % 2]:
                with section_container():
                    st.markdown(f"**◉  {escape(name)}**")
                    amount_col, share_col = st.columns([2, 1])
                    amount_col.write(format_vnd(spent))
                    share_col.caption(f"{share * 100:.0f}% chi tiêu")
                    st.caption("Hạn mức riêng: chưa được backend hỗ trợ.")
                    st.progress(share, text="Tỷ trọng chi tiêu trong tháng")
                    if spent == 0:
                        st.caption("Chưa phát sinh chi tiêu trong kỳ.")

    with section_container():
        st.markdown("**✨  Nhận xét ngân sách**")
        st.caption(
            "Chưa có API phân tích nhận xét hoặc cảnh báo ngân sách. Khi backend cung cấp dữ liệu, khu vực này có thể hiển thị insight theo giao dịch thực tế."
        )
