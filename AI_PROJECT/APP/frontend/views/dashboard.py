"""Personal finance overview rendered from the existing finance summary API."""

from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import plotly.express as px
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


_DASHBOARD_STYLES = """
<style>
.dashboard-period-note { color: #64748b; font-size: .88rem; margin: -.35rem 0 1.15rem; }
.dashboard-section-title { margin: 1.65rem 0 .2rem; color: #172b4d; font-size: 1.13rem; font-weight: 700; }
.dashboard-section-caption { color: #64748b; font-size: .86rem; margin: 0 0 .85rem; }
.dashboard-insight { border: 1px solid #dbeafe; border-left: 4px solid #2563eb; border-radius: .8rem; background: #eff6ff; padding: 1rem 1.1rem; color: #334155; }
.dashboard-insight strong { color: #1e40af; }
[data-testid="stMetric"] { min-width: 0; }
[data-testid="stMetricLabel"] p { color: #64748b; font-size: .84rem; font-weight: 600; }
[data-testid="stMetricValue"] { color: #172b4d; font-size: clamp(1.25rem, 2vw, 1.8rem); }
@media (max-width: 700px) {
    .dashboard-section-title { margin-top: 1.2rem; }
    [data-testid="stMetricValue"] { font-size: 1.2rem; }
}
</style>
"""


def _field(item: Any, name: str, default: Any = None) -> Any:
    """Read a response field from either a dict or the backend dataclass."""
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _as_records(value: Any) -> list[Any]:
    """Normalize possibly missing list fields without assuming response shape."""
    return value if isinstance(value, list) else []


def _transaction_frame(records: list[Any]) -> pd.DataFrame:
    """Build a chart-ready frame, dropping rows missing required chart fields."""
    rows = []
    for item in records:
        raw_date = _field(item, "transaction_date")
        raw_amount = _field(item, "amount_vnd")
        transaction_type = _field(item, "transaction_type")
        if raw_date is None or raw_amount is None or transaction_type not in {"income", "expense"}:
            continue
        parsed_date = pd.to_datetime(raw_date, errors="coerce")
        amount = pd.to_numeric(raw_amount, errors="coerce")
        if pd.isna(parsed_date) or pd.isna(amount):
            continue
        rows.append(
            {
                "date": parsed_date,
                "type": transaction_type,
                "amount": float(amount),
                "category": _field(item, "category_name") or "Khác",
            }
        )
    return pd.DataFrame(rows, columns=["date", "type", "amount", "category"])


def _transaction_date_key(item: Any) -> date:
    """Return a comparable date for sorting mixed backend values safely."""
    raw_date = _field(item, "transaction_date")
    if isinstance(raw_date, datetime):
        return raw_date.date()
    if isinstance(raw_date, date):
        return raw_date
    try:
        return date.fromisoformat(str(raw_date))
    except (TypeError, ValueError):
        return date.min


def _go_to_transactions() -> None:
    """Use the existing sidebar page selector to navigate to transactions."""
    st.session_state["app_page"] = "Transactions"


def render_dashboard() -> None:
    st.markdown(_DASHBOARD_STYLES, unsafe_allow_html=True)

    heading, period_col = st.columns([3, 1])
    with heading:
        render_page_header(
            "Dashboard",
            "Theo dõi dòng tiền và các khoản chi trong khoảng thời gian bạn chọn.",
        )
    with period_col:
        period = st.selectbox(
            "Khoảng thời gian",
            ["Tháng này", "Tháng trước", "Tùy chỉnh"],
            label_visibility="collapsed",
        )

    today = date.today()
    if period == "Tháng này":
        start = today.replace(day=1)
        end = today
    elif period == "Tháng trước":
        end = today.replace(day=1) - timedelta(days=1)
        start = end.replace(day=1)
    else:
        start_col, end_col = st.columns(2)
        start = start_col.date_input("Từ ngày", value=today.replace(day=1))
        end = end_col.date_input("Đến ngày", value=today)

    if start > end:
        render_error_state("Ngày bắt đầu không được sau ngày kết thúc.")
        return

    st.markdown(
        f'<div class="dashboard-period-note">Dữ liệu từ <strong>{format_date(start)}</strong> đến <strong>{format_date(end)}</strong></div>',
        unsafe_allow_html=True,
    )
    try:
        with st.spinner("Đang tổng hợp dữ liệu tài chính..."):
            result = request("finance.summary", {"start_date": start, "end_date": end})
    except Exception as error:
        render_error_state(f"Không tải được tổng quan tài chính: {error}")
        return

    if not isinstance(result, dict):
        render_error_state("Dữ liệu tổng quan chưa đúng định dạng. Vui lòng thử tải lại.")
        return

    summary = result.get("summary")
    summary = summary if isinstance(summary, dict) else {}
    metric_fields = [
        ("◈", "Số dư", "net_balance"),
        ("↗", "Tổng thu nhập", "total_income"),
        ("↘", "Tổng chi tiêu", "total_expense"),
    ]
    metric_columns = st.columns(3)
    for column, (icon, label, key) in zip(metric_columns, metric_fields):
        amount = summary.get(key)
        value = format_vnd(amount) if isinstance(amount, (int, float)) else "—"
        with column:
            render_metric_card(f"{icon}  {label}", value)

    st.markdown('<div class="dashboard-section-title">Phân tích dòng tiền</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="dashboard-section-caption">So sánh thu nhập, chi tiêu và cơ cấu chi theo dữ liệu giao dịch.</div>',
        unsafe_allow_html=True,
    )

    records = _as_records(result.get("transactions"))
    frame = _transaction_frame(records)
    chart_left, chart_right = st.columns([1.35, 1])
    with chart_left:
        with section_container():
            st.subheader("Thu nhập và chi tiêu")
            if frame.empty:
                render_empty_state("Chưa có dữ liệu giao dịch hợp lệ để vẽ biểu đồ trong kỳ này.")
            else:
                daily = (
                    frame.groupby(["date", "type"], as_index=False)["amount"]
                    .sum()
                    .sort_values("date")
                )
                daily["Loại"] = daily["type"].map(
                    {"income": "Thu nhập", "expense": "Chi tiêu"}
                )
                fig = px.line(
                    daily,
                    x="date",
                    y="amount",
                    color="Loại",
                    markers=True,
                    color_discrete_map={"Thu nhập": "#2563eb", "Chi tiêu": "#94a3b8"},
                    labels={"date": "Ngày", "amount": "Số tiền (VND)"},
                )
                fig.update_layout(
                    height=310,
                    margin=dict(l=8, r=8, t=12, b=8),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    legend_title_text="",
                    font=dict(color="#475569"),
                )
                fig.update_xaxes(showgrid=False)
                fig.update_yaxes(gridcolor="#e2e8f0", zeroline=False)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with chart_right:
        with section_container():
            st.subheader("Chi tiêu theo danh mục")
            categories = result.get("categories")
            category_rows = _as_records(
                categories.get("categories") if isinstance(categories, dict) else None
            )
            valid_categories = []
            for item in category_rows:
                name = _field(item, "category")
                amount = _field(item, "amount")
                if isinstance(name, str) and isinstance(amount, (int, float)) and amount > 0:
                    valid_categories.append({"Danh mục": name, "Số tiền": amount})
            if not valid_categories:
                render_empty_state("Chưa có khoản chi theo danh mục trong kỳ này.")
            else:
                category_frame = pd.DataFrame(valid_categories)
                fig = px.pie(
                    category_frame,
                    names="Danh mục",
                    values="Số tiền",
                    hole=0.62,
                    color_discrete_sequence=px.colors.sequential.Blues[2:],
                )
                fig.update_traces(textposition="inside", textinfo="percent")
                fig.update_layout(
                    height=310,
                    margin=dict(l=8, r=8, t=12, b=8),
                    paper_bgcolor="rgba(0,0,0,0)",
                    legend_title_text="",
                    font=dict(color="#475569"),
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="dashboard-section-title">Góc nhìn tài chính</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="dashboard-insight"><strong>Thông tin hiện có</strong><br>Dashboard đang hiển thị số liệu và phân tích từ các giao dịch trong kỳ. Backend hiện chưa cung cấp API nhận xét hoặc cảnh báo tài chính.</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="dashboard-section-title">Giao dịch gần đây</div>', unsafe_allow_html=True)
    recent_records = [
        item
        for item in records
        if _transaction_date_key(item) != date.min
        and _field(item, "transaction_type") in {"income", "expense"}
        and isinstance(_field(item, "amount_vnd"), (int, float))
    ]
    recent = sorted(
        recent_records,
        key=_transaction_date_key,
        reverse=True,
    )[:5]
    if not recent:
        render_empty_state("Chưa có giao dịch trong khoảng thời gian này.")
    else:
        recent_rows = []
        for item in recent:
            raw_date = _field(item, "transaction_date")
            if isinstance(raw_date, datetime):
                display_date = raw_date.date()
            elif isinstance(raw_date, date):
                display_date = raw_date
            else:
                try:
                    display_date = date.fromisoformat(str(raw_date))
                except (TypeError, ValueError):
                    display_date = None
            transaction_type = _field(item, "transaction_type")
            amount = _field(item, "amount_vnd")
            recent_rows.append(
                {
                    "Ngày": format_date(display_date) if display_date else "—",
                    "Giao dịch": _field(item, "description") or "Giao dịch",
                    "Danh mục": _field(item, "category_name") or "—",
                    "Loại": {
                        "income": "Thu nhập",
                        "expense": "Chi tiêu",
                    }.get(transaction_type, "—"),
                    "Số tiền": format_vnd(amount) if isinstance(amount, (int, float)) else "—",
                }
            )
        st.dataframe(pd.DataFrame(recent_rows), hide_index=True, use_container_width=True)
        st.button(
            "Xem tất cả giao dịch",
            on_click=_go_to_transactions,
            type="secondary",
        )
