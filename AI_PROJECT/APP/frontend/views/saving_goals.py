"""Saving goals page using the existing goal commands and response fields."""

from datetime import date
from html import escape
from typing import Any

import streamlit as st

from frontend.api_client import request
from frontend.components.design_system import (
    render_empty_state,
    render_error_state,
    render_page_header,
    section_container,
)
from utils.formatting import format_date, format_vnd


GOAL_STATUS_LABELS = {
    "active": "Đang thực hiện",
    "finished": "Hoàn thành",
    "failed": "Chưa đạt",
    "cancelled": "Đã hủy",
}

_SAVING_GOALS_STYLES = """
<style>
.goals-summary { min-height: 118px; }
.goals-summary-head { display:flex; align-items:center; gap:.65rem; }
.goals-summary-icon { display:grid; width:2.15rem; height:2.15rem; place-items:center; border-radius:.72rem; background:#eef5ff; color:#3984e8; font-size:1rem; font-weight:750; }
.goals-summary-label { color:#8491a3; font-size:.82rem; font-weight:650; }
.goals-summary-value { margin-top:.7rem; color:#202938; font-size:clamp(1.2rem,2vw,1.65rem); font-weight:760; letter-spacing:-.025em; }
.goals-summary-foot { margin-top:.2rem; color:#8491a3; font-size:.75rem; }
.goal-card-top { display:flex; justify-content:space-between; align-items:flex-start; gap:.7rem; }
.goal-card-title { color:#202938; font-size:1rem; font-weight:730; line-height:1.35; overflow-wrap:anywhere; }
.goal-card-subtitle { margin-top:.2rem; color:#8491a3; font-size:.78rem; }
.goal-card-icon { display:grid; flex:0 0 2.55rem; width:2.55rem; height:2.55rem; place-items:center; border-radius:.85rem; background:#eef5ff; color:#3984e8; font-size:1.1rem; font-weight:750; }
.goal-card-status { flex:0 0 auto; border-radius:999px; padding:.22rem .58rem; background:#eef5ff; color:#2563eb; font-size:.7rem; font-weight:700; white-space:nowrap; }
.goal-card-status-finished { background:#eaf7f0; color:#168451; }
.goal-card-status-failed,.goal-card-status-cancelled { background:#f1f3f6; color:#64748b; }
.goal-amount { margin-top:.9rem; color:#202938; font-size:1.35rem; font-weight:760; letter-spacing:-.025em; }
.goal-amount-caption { color:#8491a3; font-size:.78rem; }
.goal-card-meta { display:flex; justify-content:space-between; gap:.5rem; margin-top:.45rem; color:#64748b; font-size:.78rem; }
.goal-card-remaining { margin-top:.25rem; color:#64748b; font-size:.78rem; }
.goal-section-title { margin:1.35rem 0 .2rem; color:#202938; font-size:1.1rem; font-weight:730; }
.goal-section-caption { margin:0 0 .7rem; color:#8491a3; font-size:.82rem; }
.goal-empty { padding:.45rem .2rem; text-align:center; }
.goal-empty-icon { display:grid; width:3.15rem; height:3.15rem; margin:0 auto .7rem; place-items:center; border-radius:1rem; background:#eef5ff; color:#3984e8; font-size:1.4rem; font-weight:750; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color:#e7edf5; border-radius:15px; background:#fff; box-shadow:0 4px 16px rgba(34,63,100,.045); transition:border-color .16s ease,box-shadow .16s ease,transform .16s ease; }
[data-testid="stVerticalBlockBorderWrapper"]:hover { border-color:#d8e4f3; box-shadow:0 7px 20px rgba(34,63,100,.075); }
[data-testid="stMetricLabel"] p { color:#8491a3; font-size:.82rem; font-weight:600; }
@media(max-width:700px) { .goals-summary { min-height:104px; } .goal-amount { font-size:1.2rem; } .goal-card-meta { font-size:.74rem; } }
</style>
"""


def _field(goal: Any, name: str, default: Any = None) -> Any:
    """Read a field from the current dataclass or a mapping response."""
    if isinstance(goal, dict):
        return goal.get(name, default)
    return getattr(goal, name, default)


def _amount(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def _safe_format_date(value: Any) -> str:
    if isinstance(value, date):
        return format_date(value)
    if value:
        try:
            return format_date(date.fromisoformat(str(value)[:10]))
        except (TypeError, ValueError):
            return "Chưa có ngày hợp lệ"
    return "Chưa đặt hạn"


def _render_summary_card(icon: str, label: str, value: str, footnote: str) -> None:
    with section_container():
        st.markdown(
            f'<div class="goals-summary"><div class="goals-summary-head">'
            f'<span class="goals-summary-icon">{icon}</span>'
            f'<span class="goals-summary-label">{escape(label)}</span></div>'
            f'<div class="goals-summary-value">{escape(value)}</div>'
            f'<div class="goals-summary-foot">{escape(footnote)}</div></div>',
            unsafe_allow_html=True,
        )


def _render_goal_card(goal: Any) -> None:
    name = str(_field(goal, "name", "Mục tiêu"))
    status = str(_field(goal, "status", "unknown"))
    status_label = GOAL_STATUS_LABELS.get(status, "Chưa xác định")
    target = max(0, _amount(_field(goal, "target_amount_vnd")))
    progress = _amount(_field(goal, "progress_vnd"))
    remaining = max(target - progress, 0)
    ratio = max(0.0, min(progress / target, 1.0)) if target else 0.0
    deadline = _safe_format_date(_field(goal, "deadline"))
    status_class = status if status in GOAL_STATUS_LABELS else "unknown"

    with section_container():
        st.markdown(
            f'<div class="goal-card-top"><div style="display:flex;gap:.7rem;min-width:0">'
            f'<span class="goal-card-icon">↗</span><div style="min-width:0">'
            f'<div class="goal-card-title">{escape(name)}</div>'
            f'<div class="goal-card-subtitle">Hạn mục tiêu · {escape(deadline)}</div></div></div>'
            f'<span class="goal-card-status goal-card-status-{status_class}">{escape(status_label)}</span></div>'
            f'<div class="goal-amount">{escape(format_vnd(progress))}</div>'
            f'<div class="goal-amount-caption">đã tích lũy trên {escape(format_vnd(target))}</div>',
            unsafe_allow_html=True,
        )
        st.progress(ratio, text=f"{ratio:.0%} hoàn thành")
        st.markdown(
            f'<div class="goal-card-meta"><span>Còn thiếu</span>'
            f'<strong>{escape(format_vnd(remaining))}</strong></div>',
            unsafe_allow_html=True,
        )


def _render_create_form(active_goals: list[Any]) -> None:
    if active_goals:
        st.info("Bạn đã có mục tiêu đang thực hiện. Hãy kết thúc mục tiêu đó trước khi tạo mục tiêu mới.")
        return

    with section_container():
        st.markdown('<div class="goal-section-title">Thông tin mục tiêu</div>', unsafe_allow_html=True)
        st.caption("Đặt tên, số tiền và hạn hoàn thành cho kế hoạch của bạn.")
        with st.form("saving_goal_create_form", clear_on_submit=True):
            name = st.text_input("Tên mục tiêu", max_chars=150, placeholder="Ví dụ: Học phí học kỳ tới")
            target = st.number_input("Số tiền mục tiêu (VND)", min_value=1, step=100_000)
            deadline = st.date_input("Hạn hoàn thành")
            create = st.form_submit_button("Tạo mục tiêu", type="primary", use_container_width=True)
        if create:
            if target <= 0:
                st.error("Số tiền mục tiêu phải lớn hơn 0 VND.")
            else:
                try:
                    with st.spinner("Đang tạo mục tiêu..."):
                        request("goal.create", {
                            "name": name, "target_amount_vnd": int(target), "deadline": deadline
                        })
                    st.session_state["saving_goals_create_open"] = False
                    st.success("Đã tạo mục tiêu.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Không thể tạo mục tiêu: {error}")


def _render_goal_management(goals: list[Any]) -> None:
    editable = [goal for goal in goals if _field(goal, "status") == "active"]
    if not editable:
        return

    st.markdown('<div class="goal-section-title">Quản lý mục tiêu</div>', unsafe_allow_html=True)
    selected = st.selectbox(
        "Chọn mục tiêu đang thực hiện",
        editable,
        format_func=lambda goal: str(_field(goal, "name", "Mục tiêu")),
        label_visibility="collapsed",
    )
    with st.expander("Chỉnh sửa số tiền và hạn hoàn thành"):
        current_target = max(1, _amount(_field(selected, "target_amount_vnd"), 1))
        current_deadline = _field(selected, "deadline")
        if not isinstance(current_deadline, date):
            try:
                current_deadline = date.fromisoformat(str(current_deadline)[:10])
            except (TypeError, ValueError):
                current_deadline = date.today()
        with st.form(f"edit_goal_{_field(selected, 'goal_id')}"):
            target = st.number_input(
                "Số tiền mục tiêu (VND)", min_value=1, value=current_target, step=100_000,
            )
            deadline = st.date_input("Hạn hoàn thành", value=current_deadline)
            save = st.form_submit_button("Lưu thay đổi", type="primary")
        if save:
            if target <= 0:
                st.error("Số tiền mục tiêu phải lớn hơn 0 VND.")
            else:
                try:
                    result = request("goal.update", {
                        "goal_id": _field(selected, "goal_id"),
                        "target_amount_vnd": int(target),
                        "deadline": deadline,
                    })
                    if result is None:
                        st.error("Không tìm thấy mục tiêu đang hoạt động.")
                    else:
                        st.success("Đã cập nhật mục tiêu.")
                        st.rerun()
                except Exception as error:
                    st.error(f"Không thể cập nhật mục tiêu: {error}")
    if st.button("Hủy mục tiêu", key=f"cancel_goal_{_field(selected, 'goal_id')}"):
        try:
            result = request("goal.cancel", {"goal_id": _field(selected, "goal_id")})
            if result is None:
                st.error("Không tìm thấy mục tiêu để hủy.")
            else:
                st.success("Đã hủy mục tiêu.")
                st.rerun()
        except Exception as error:
            st.error(f"Không thể hủy mục tiêu: {error}")


def render_saving_goals() -> None:
    st.markdown(_SAVING_GOALS_STYLES, unsafe_allow_html=True)
    try:
        with st.spinner("Đang tải mục tiêu..."):
            response = request("goal.list")
    except Exception as error:
        render_page_header("Mục tiêu tiết kiệm", "Theo dõi kế hoạch và tiến độ tích lũy của bạn.")
        render_error_state(f"Không tải được mục tiêu: {error}")
        return

    goals = response if isinstance(response, (list, tuple)) else []
    valid_goals = [goal for goal in goals if _field(goal, "goal_id") is not None]
    active_goals = [goal for goal in valid_goals if _field(goal, "status") == "active"]
    finished_goals = [goal for goal in valid_goals if _field(goal, "status") == "finished"]
    total_saved = sum(_amount(_field(goal, "progress_vnd")) for goal in valid_goals)
    total_target = sum(max(0, _amount(_field(goal, "target_amount_vnd"))) for goal in valid_goals)

    header_text, action = st.columns([4, 1], vertical_alignment="center")
    with header_text:
        render_page_header(
            "Mục tiêu tiết kiệm",
            "Biến kế hoạch tài chính thành những cột mốc rõ ràng và dễ theo dõi.",
        )
    create_open = st.session_state.get("saving_goals_create_open", False)
    with action:
        if valid_goals:
            if st.button("Đóng" if create_open else "+ Tạo mục tiêu", type="primary", use_container_width=True):
                st.session_state["saving_goals_create_open"] = not create_open
                st.rerun()

    summary = st.columns(4)
    with summary[0]:
        _render_summary_card("↗", "Đã tích lũy", format_vnd(total_saved), "Tổng tiến độ các mục tiêu")
    with summary[1]:
        _render_summary_card("◎", "Tổng mục tiêu", format_vnd(total_target), "Theo các kế hoạch hiện có")
    with summary[2]:
        _render_summary_card("◷", "Đang thực hiện", str(len(active_goals)), "Mục tiêu đang mở")
    with summary[3]:
        _render_summary_card("✓", "Đã hoàn thành", str(len(finished_goals)), "Mục tiêu đạt trạng thái hoàn thành")

    if create_open and valid_goals:
        _render_create_form(active_goals)

    st.markdown('<div class="goal-section-title">Kế hoạch của bạn</div>', unsafe_allow_html=True)
    st.markdown('<div class="goal-section-caption">Theo dõi số tiền đã góp, tiến độ và ngày mục tiêu.</div>', unsafe_allow_html=True)
    if not valid_goals:
        with section_container():
            st.markdown(
                '<div class="goal-empty"><div class="goal-empty-icon">◎</div>'
                '<strong>Chưa có mục tiêu tiết kiệm</strong><br>'
                '<span style="color:#8491a3;font-size:.86rem">Tạo mục tiêu đầu tiên để bắt đầu theo dõi kế hoạch của bạn.</span></div>',
                unsafe_allow_html=True,
            )
            if st.button("+ Tạo mục tiêu đầu tiên", type="primary", use_container_width=True):
                st.session_state["saving_goals_create_open"] = True
                st.rerun()
        if st.session_state.get("saving_goals_create_open", False):
            _render_create_form(active_goals)
        return

    labels = ["Tất cả", *GOAL_STATUS_LABELS.values()]
    selected_label = st.selectbox("Lọc trạng thái", labels, label_visibility="collapsed")
    status_by_label = {label: status for status, label in GOAL_STATUS_LABELS.items()}
    visible = [
        goal for goal in valid_goals
        if selected_label == "Tất cả" or _field(goal, "status") == status_by_label[selected_label]
    ]
    if not visible:
        render_empty_state("Không có mục tiêu nào thuộc trạng thái này.")
    else:
        for start in range(0, len(visible), 2):
            columns = st.columns(2)
            for column, goal in zip(columns, visible[start:start + 2]):
                with column:
                    _render_goal_card(goal)

    if valid_goals:
        st.info("Lịch sử đóng góp chi tiết chưa được cung cấp bởi API Saving Goals hiện tại.")
    _render_goal_management(valid_goals)
