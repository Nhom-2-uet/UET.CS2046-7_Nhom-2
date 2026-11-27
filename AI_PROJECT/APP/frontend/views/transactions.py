"""Transaction list, filters and existing create/update/delete workflows."""

from datetime import date, datetime, timedelta
from html import escape
from typing import Any

import streamlit as st

from frontend.api_client import request
from frontend.components.design_system import (
    render_empty_state,
    render_error_state,
    render_metric_card,
    render_page_header,
    section_container,
)
from utils.formatting import format_date, format_vnd


TYPE_LABELS = {"expense": "Chi tiêu", "income": "Thu nhập"}
TYPE_VALUES = {label: value for value, label in TYPE_LABELS.items()}

_TRANSACTION_STYLES = """
<style>
.transactions-period-note { color: #8491a3; font-size: .86rem; margin: -.3rem 0 .75rem; }
.transactions-section-title { margin: 1.45rem 0 .2rem; color: #202938; font-size: 1.08rem; font-weight: 700; }
.transactions-section-caption { margin: 0 0 .8rem; color: #8491a3; font-size: .86rem; }
.transaction-kind { display: inline-block; border-radius: 999px; padding: .2rem .58rem; font-size: .76rem; font-weight: 650; }
.transaction-income { color: #168451; background: #e8f7ef; }
.transaction-expense { color: #c94a42; background: #fff0ef; }
.transaction-unknown { color: #64748b; background: #eef2f7; }
.transaction-amount { margin-top: .2rem; font-size: 1.18rem; font-weight: 700; white-space: nowrap; }
.transaction-amount-income { color: #168451; }
.transaction-amount-expense { color: #202938; }
.transaction-amount-unknown { color: #64748b; }
[data-testid="stMetricLabel"] p { color: #8491a3; font-size: .82rem; font-weight: 600; }
[data-testid="stMetricValue"] { color: #202938; font-size: clamp(1.15rem, 2vw, 1.55rem); }
@media (max-width: 700px) {
    .transactions-section-title { margin-top: 1.1rem; }
    .transaction-amount { font-size: 1.05rem; }
    [data-testid="stMetricValue"] { font-size: 1.1rem; }
}
</style>
"""


def _field(record: Any, name: str, default: Any = None) -> Any:
    if isinstance(record, dict):
        return record.get(name, default)
    return getattr(record, name, default)


def _amount(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        amount = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return amount if amount >= 0 else None


def _parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value is None:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _record_dict(record: Any) -> dict[str, Any]:
    """Normalize a transaction model or mapping for consistent page rendering."""
    return {
        "transaction_id": _field(record, "transaction_id"),
        "transaction_date": _parse_date(_field(record, "transaction_date")),
        "description": str(_field(record, "description") or "").strip(),
        "category_name": _field(record, "category_name"),
        "transaction_type": _field(record, "transaction_type"),
        "amount_vnd": _amount(_field(record, "amount_vnd")),
    }


def _load_categories(transaction_type: str) -> list[str]:
    """Load only category names returned by the existing categories command."""
    result = request("transaction.categories", {"transaction_type": transaction_type})
    if not isinstance(result, list):
        raise TypeError("API danh mục không trả về danh sách.")
    return sorted(
        {
            row["name"].strip()
            for row in result
            if isinstance(row, dict)
            and isinstance(row.get("name"), str)
            and row["name"].strip()
        }
    )


def _open_add_form() -> None:
    st.session_state["transaction_add_open"] = True


def _clear_filters() -> None:
    st.session_state["transaction_search"] = ""
    st.session_state["transaction_period"] = "Toàn thời gian"
    st.session_state["transaction_type_filter"] = "Tất cả"
    st.session_state["transaction_category_filter"] = "Tất cả"
    st.session_state["transaction_start_date"] = date.today().replace(day=1)
    st.session_state["transaction_end_date"] = date.today()


def _month_bounds(value: date, offset: int = 0) -> tuple[date, date]:
    month_index = value.year * 12 + value.month - 1 + offset
    year, month_index = divmod(month_index, 12)
    start = date(year, month_index + 1, 1)
    next_month_index = year * 12 + month_index + 1
    next_year, next_month_index = divmod(next_month_index, 12)
    end = date(next_year, next_month_index + 1, 1) - timedelta(days=1)
    return start, end


def _show_add_form() -> None:
    with st.expander(
        "Thêm giao dịch mới",
        expanded=st.session_state.get("transaction_add_open", False),
    ):
        type_label = st.selectbox(
            "Loại giao dịch",
            list(TYPE_VALUES),
            key="new_transaction_type",
        )
        transaction_type = TYPE_VALUES[type_label]
        try:
            categories = _load_categories(transaction_type)
        except Exception as error:
            categories = []
            render_error_state(f"Không tải được danh mục: {error}")
        if not categories:
            st.info("Chưa có danh mục đang hoạt động cho loại giao dịch này.")

        with st.form("add_transaction_form", clear_on_submit=True):
            name = st.text_input("Tên giao dịch", placeholder="Ví dụ: Ăn sáng")
            amount = st.number_input("Số tiền (VND)", min_value=1, step=1_000)
            transaction_date = st.date_input("Ngày giao dịch", value=date.today())
            category = st.selectbox(
                "Danh mục", categories, disabled=not categories
            )
            submitted = st.form_submit_button(
                "Thêm giao dịch",
                type="primary",
                disabled=not categories,
                use_container_width=True,
            )
        if submitted:
            if not name.strip() or amount <= 0:
                render_error_state("Vui lòng nhập tên giao dịch và số tiền lớn hơn 0.")
            else:
                try:
                    with st.spinner("Đang lưu giao dịch..."):
                        request(
                            "transaction.create",
                            {
                                "description": name.strip(),
                                "amount_vnd": int(amount),
                                "transaction_date": transaction_date,
                                "category_name": category,
                                "transaction_type": transaction_type,
                            },
                        )
                    st.session_state["transaction_add_open"] = False
                    st.session_state["transaction_notice"] = (
                        "success",
                        "Đã thêm giao dịch.",
                    )
                    st.rerun()
                except Exception as error:
                    render_error_state(f"Không thể thêm giao dịch: {error}")


def _edit_transaction(record: dict[str, Any]) -> None:
    transaction_id = record["transaction_id"]
    if not isinstance(transaction_id, int):
        render_error_state("Giao dịch này thiếu mã hợp lệ nên không thể chỉnh sửa.")
        return

    with section_container():
        st.markdown("**Chỉnh sửa giao dịch**")
        current_type = record["transaction_type"]
        current_type_label = TYPE_LABELS.get(current_type, "Chi tiêu")
        type_label = st.selectbox(
            "Loại giao dịch",
            list(TYPE_VALUES),
            index=list(TYPE_VALUES).index(current_type_label),
            key=f"edit_type_{transaction_id}",
        )
        edit_type = TYPE_VALUES[type_label]
        categories_error = None
        try:
            edit_categories = _load_categories(edit_type)
        except Exception as error:
            edit_categories = []
            categories_error = error
            render_error_state(f"Không tải được danh mục: {error}")
        current_category = record["category_name"]
        if (
            edit_type == current_type
            and isinstance(current_category, str)
            and current_category not in edit_categories
        ):
            edit_categories.append(current_category)
        if edit_categories and current_category in edit_categories:
            category_index = edit_categories.index(current_category)
        else:
            category_index = 0

        with st.form(f"edit_transaction_{transaction_id}"):
            edit_name = st.text_input(
                "Tên giao dịch",
                value=record["description"],
                key=f"edit_name_{transaction_id}",
            )
            edit_amount = st.number_input(
                "Số tiền (VND)",
                min_value=1,
                value=max(1, record["amount_vnd"] or 1),
                step=1_000,
                key=f"edit_amount_{transaction_id}",
            )
            current_date = record["transaction_date"] or date.today()
            edit_date = st.date_input(
                "Ngày giao dịch",
                value=current_date,
                key=f"edit_date_{transaction_id}",
            )
            edit_category = st.selectbox(
                "Danh mục",
                edit_categories,
                index=category_index,
                disabled=not edit_categories,
                key=f"edit_category_{transaction_id}",
            )
            save = st.form_submit_button(
                "Lưu thay đổi",
                type="primary",
                disabled=not edit_categories or categories_error is not None,
            )
            cancel = st.form_submit_button("Hủy")

        if cancel:
            st.session_state["transaction_edit_id"] = None
            st.rerun()
        if save:
            if not edit_name.strip() or edit_amount <= 0:
                render_error_state("Vui lòng nhập tên giao dịch và số tiền lớn hơn 0.")
            else:
                try:
                    with st.spinner("Đang cập nhật giao dịch..."):
                        updated = request(
                            "transaction.update",
                            {
                                "transaction_id": int(transaction_id),
                                "description": edit_name.strip(),
                                "amount_vnd": int(edit_amount),
                                "transaction_date": edit_date,
                                "category_name": edit_category,
                                "transaction_type": edit_type,
                            },
                        )
                    if updated is None:
                        render_error_state("Không tìm thấy giao dịch để cập nhật.")
                    else:
                        st.session_state["transaction_edit_id"] = None
                        st.session_state["transaction_notice"] = (
                            "success",
                            "Đã cập nhật giao dịch.",
                        )
                        st.rerun()
                except Exception as error:
                    render_error_state(f"Không thể cập nhật giao dịch: {error}")


def _confirm_delete(record: dict[str, Any]) -> None:
    transaction_id = record["transaction_id"]
    if not isinstance(transaction_id, int):
        render_error_state("Giao dịch này thiếu mã hợp lệ nên không thể xóa.")
        return
    with section_container():
        st.warning(
            f"Bạn sắp xóa giao dịch “{record['description'] or 'Giao dịch'}”. Thao tác này không thể hoàn tác."
        )
        cancel_col, delete_col = st.columns([1, 1])
        if cancel_col.button("Giữ lại", key="cancel_transaction_delete"):
            st.session_state["transaction_delete_id"] = None
            st.rerun()
        if delete_col.button(
            "Xác nhận xóa",
            key="confirm_transaction_delete",
            type="primary",
        ):
            try:
                with st.spinner("Đang xóa giao dịch..."):
                    deleted = request(
                        "transaction.delete", {"transaction_id": int(transaction_id)}
                    )
                if deleted:
                    st.session_state["transaction_delete_id"] = None
                    st.session_state["transaction_notice"] = (
                        "success",
                        "Đã xóa giao dịch.",
                    )
                    st.rerun()
                else:
                    render_error_state("Không tìm thấy giao dịch để xóa.")
            except Exception as error:
                render_error_state(f"Không thể xóa giao dịch: {error}")


def render_transactions() -> None:
    st.markdown(_TRANSACTION_STYLES, unsafe_allow_html=True)
    if "transaction_add_open" not in st.session_state:
        st.session_state["transaction_add_open"] = False

    header, action = st.columns([3, 1])
    with header:
        render_page_header(
            "Giao dịch",
            "Theo dõi các khoản thu chi và quản lý lịch sử giao dịch của bạn.",
        )
    action.button(
        "＋  Thêm giao dịch",
        type="primary",
        use_container_width=True,
        on_click=_open_add_form,
    )

    notice = st.session_state.pop("transaction_notice", None)
    if notice:
        if notice[0] == "success":
            st.success(notice[1])
        else:
            render_error_state(notice[1])

    _show_add_form()

    try:
        with st.spinner("Đang tải giao dịch..."):
            records = request("transaction.list")
        if not isinstance(records, list):
            raise TypeError("API transaction.list không trả về danh sách.")
    except Exception as error:
        render_error_state(f"Không tải được danh sách giao dịch: {error}")
        return

    transactions = [_record_dict(record) for record in records]
    valid_categories = sorted(
        {
            transaction["category_name"]
            for transaction in transactions
            if isinstance(transaction["category_name"], str)
            and transaction["category_name"].strip()
        }
    )
    category_options = ["Tất cả", *valid_categories]
    if st.session_state.get("transaction_category_filter", "Tất cả") not in category_options:
        st.session_state["transaction_category_filter"] = "Tất cả"
    if "transaction_period" not in st.session_state:
        st.session_state["transaction_period"] = "Toàn thời gian"
    if "transaction_type_filter" not in st.session_state:
        st.session_state["transaction_type_filter"] = "Tất cả"
    if "transaction_search" not in st.session_state:
        st.session_state["transaction_search"] = ""

    st.markdown(
        '<div class="transactions-section-title">Bộ lọc và tìm kiếm</div>',
        unsafe_allow_html=True,
    )
    with section_container():
        period_col, type_col, category_col = st.columns([1.25, 1, 1.2])
        period = period_col.selectbox(
            "Khoảng thời gian",
            ["Toàn thời gian", "Tháng này", "Tháng trước", "Tùy chỉnh"],
            key="transaction_period",
        )
        type_label = type_col.selectbox(
            "Loại giao dịch",
            ["Tất cả", *TYPE_VALUES],
            format_func=lambda value: value if value == "Tất cả" else value,
            key="transaction_type_filter",
        )
        category_name = category_col.selectbox(
            "Danh mục",
            category_options,
            key="transaction_category_filter",
        )
        date_start = date_end = None
        today = date.today()
        if period == "Tháng này":
            date_start, date_end = _month_bounds(today)
        elif period == "Tháng trước":
            date_start, date_end = _month_bounds(today, -1)
        elif period == "Tùy chỉnh":
            if "transaction_start_date" not in st.session_state:
                st.session_state["transaction_start_date"] = today.replace(day=1)
            if "transaction_end_date" not in st.session_state:
                st.session_state["transaction_end_date"] = today
            start_col, end_col = st.columns(2)
            date_start = start_col.date_input(
                "Từ ngày", key="transaction_start_date"
            )
            date_end = end_col.date_input(
                "Đến ngày", key="transaction_end_date"
            )
        search_col, clear_col = st.columns([4, 1])
        search = search_col.text_input(
            "Tìm giao dịch",
            placeholder="Tìm theo tên giao dịch...",
            key="transaction_search",
        )
        clear_col.button(
            "Xóa bộ lọc",
            on_click=_clear_filters,
            use_container_width=True,
        )

    if date_start and date_end and date_start > date_end:
        render_error_state("Ngày bắt đầu không được sau ngày kết thúc.")
        return

    filtered = transactions
    if date_start:
        filtered = [
            item
            for item in filtered
            if item["transaction_date"] is not None
            and date_start <= item["transaction_date"] <= date_end
        ]
    if type_label != "Tất cả":
        filtered = [
            item for item in filtered
            if item["transaction_type"] == TYPE_VALUES[type_label]
        ]
    if category_name != "Tất cả":
        filtered = [
            item for item in filtered if item["category_name"] == category_name
        ]
    if search:
        query = search.casefold()
        filtered = [
            item for item in filtered
            if query in item["description"].casefold()
        ]

    period_label = (
        f"{format_date(date_start)} – {format_date(date_end)}"
        if date_start and date_end
        else "Tất cả thời gian"
    )
    st.markdown(
        f'<div class="transactions-period-note">Đang xem: {escape(period_label)} · {len(filtered)} giao dịch</div>',
        unsafe_allow_html=True,
    )

    income_total = sum(
        item["amount_vnd"] or 0
        for item in filtered
        if item["transaction_type"] == "income"
    )
    expense_total = sum(
        item["amount_vnd"] or 0
        for item in filtered
        if item["transaction_type"] == "expense"
    )
    metrics = st.columns(4)
    metric_values = [
        ("↑  Tổng thu", format_vnd(income_total)),
        ("↓  Tổng chi", format_vnd(expense_total)),
        ("Chênh lệch", format_vnd(income_total - expense_total)),
        ("Số giao dịch", f"{len(filtered):,}"),
    ]
    for column, (label, value) in zip(metrics, metric_values):
        with column:
            render_metric_card(label, value)

    st.markdown(
        '<div class="transactions-section-title">Danh sách giao dịch</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="transactions-section-caption">Các khoản thu và chi được sắp xếp theo ngày mới nhất.</div>',
        unsafe_allow_html=True,
    )
    filtered.sort(
        key=lambda item: item["transaction_date"] or date.min,
        reverse=True,
    )
    if not filtered:
        if transactions:
            render_empty_state("Không tìm thấy giao dịch phù hợp với bộ lọc.")
            st.button("Xóa bộ lọc và xem tất cả", on_click=_clear_filters)
        else:
            render_empty_state("Bạn chưa có giao dịch nào. Thêm giao dịch đầu tiên để bắt đầu theo dõi.")
        return

    for offset in range(0, len(filtered), 2):
        card_columns = st.columns(2)
        for column, item in zip(card_columns, filtered[offset : offset + 2]):
            with column:
                with section_container():
                    top, amount_col = st.columns([3, 1.35])
                    description = escape(item["description"] or "Giao dịch")
                    top.markdown(f"**{description}**")
                    date_text = (
                        format_date(item["transaction_date"])
                        if item["transaction_date"]
                        else "Chưa có ngày"
                    )
                    category_text = escape(str(item["category_name"] or "—"))
                    top.caption(f"{category_text}  ·  {date_text}")
                    transaction_type = item["transaction_type"]
                    kind_label = TYPE_LABELS.get(transaction_type, "Không xác định")
                    kind_class = (
                        "transaction-income"
                        if transaction_type == "income"
                        else "transaction-expense"
                        if transaction_type == "expense"
                        else "transaction-unknown"
                    )
                    amount_class = (
                        "transaction-amount-income"
                        if transaction_type == "income"
                        else "transaction-amount-expense"
                        if transaction_type == "expense"
                        else "transaction-amount-unknown"
                    )
                    amount_text = (
                        format_vnd(item["amount_vnd"])
                        if item["amount_vnd"] is not None
                        else "—"
                    )
                    sign = "+" if transaction_type == "income" else "−" if transaction_type == "expense" else ""
                    amount_col.markdown(
                        f'<div class="transaction-amount {amount_class}">{sign}{amount_text}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<span class="transaction-kind {kind_class}">{kind_label}</span>',
                        unsafe_allow_html=True,
                    )
                    edit_col, delete_col = st.columns(2)
                    if edit_col.button(
                        "Chỉnh sửa",
                        key=f"transaction_edit_{item['transaction_id']}",
                        use_container_width=True,
                        disabled=not isinstance(item["transaction_id"], int),
                    ):
                        st.session_state["transaction_edit_id"] = item["transaction_id"]
                        st.session_state["transaction_delete_id"] = None
                    if delete_col.button(
                        "Xóa",
                        key=f"transaction_delete_{item['transaction_id']}",
                        use_container_width=True,
                        disabled=not isinstance(item["transaction_id"], int),
                    ):
                        st.session_state["transaction_delete_id"] = item["transaction_id"]
                        st.session_state["transaction_edit_id"] = None

    selected_edit = next(
        (
            item for item in filtered
            if item["transaction_id"] == st.session_state.get("transaction_edit_id")
        ),
        None,
    )
    selected_delete = next(
        (
            item for item in filtered
            if item["transaction_id"] == st.session_state.get("transaction_delete_id")
        ),
        None,
    )
    if selected_edit:
        _edit_transaction(selected_edit)
    elif selected_delete:
        _confirm_delete(selected_delete)
