from datetime import date, datetime

import pandas as pd
import streamlit as st

from utils.formatting import format_date, format_vnd


GOAL_STATUS_LABELS = {
    "active": "Đang thực hiện",
    "finished": "Hoàn thành",
    "failed": "Không đạt",
    "cancelled": "Đã hủy",
}


def _initialize_mock_state() -> None:
    """Initialize session-local goals without inventing a Backend user ID."""
    if "saving_goals_mock" not in st.session_state:
        st.session_state["saving_goals_mock"] = []

    goals = st.session_state["saving_goals_mock"]
    next_id = max((goal["goal_id"] for goal in goals), default=0) + 1
    st.session_state.setdefault("saving_goals_next_mock_id", next_id)


def _find_goal(goal_id: int) -> dict | None:
    return next(
        (
            goal
            for goal in st.session_state["saving_goals_mock"]
            if goal["goal_id"] == goal_id
        ),
        None,
    )


def render_saving_goals() -> None:
    """Render mock Saving Goals management UI."""
    _initialize_mock_state()
    st.header("Mục tiêu tiết kiệm")
    st.caption("Thiết lập và theo dõi các mục tiêu tiết kiệm của bạn.")

    flash_message = st.session_state.pop("saving_goals_flash", None)
    if flash_message:
        st.success(flash_message)

    goals = st.session_state["saving_goals_mock"]
    active_goals = [goal for goal in goals if goal["status"] == "active"]

    with st.container(border=True):
        st.subheader("Tạo mục tiêu tiết kiệm")
        if active_goals:
            st.info(
                "Bạn đang có một mục tiêu hoạt động. Hãy hoàn thành hoặc hủy mục tiêu đó "
                "trước khi tạo mục tiêu mới."
            )

        with st.form("saving_goal_create_form", clear_on_submit=True):
            name = st.text_input("Tên mục tiêu", max_chars=150)
            target_amount = st.number_input(
                "Số tiền mục tiêu (VND)", min_value=0, step=100_000
            )
            deadline = st.date_input("Deadline", value=date.today())
            submitted = st.form_submit_button(
                "Tạo mục tiêu", disabled=bool(active_goals)
            )

        if submitted:
            if not name.strip():
                st.error("Vui lòng nhập tên mục tiêu.")
            elif target_amount <= 0:
                st.error("Số tiền mục tiêu phải lớn hơn 0 VND.")
            elif any(
                goal["status"] == "active"
                for goal in st.session_state["saving_goals_mock"]
            ):
                st.error("Chỉ được có một mục tiêu đang thực hiện tại một thời điểm.")
            else:
                goal_id = st.session_state["saving_goals_next_mock_id"]
                st.session_state["saving_goals_next_mock_id"] += 1
                st.session_state["saving_goals_mock"].append(
                    {
                        # Session-local mock ID; it is not a Backend goal_id.
                        "goal_id": goal_id,
                        "name": name.strip(),
                        "target_amount_vnd": int(target_amount),
                        "deadline": deadline,
                        "status": "active",
                        "created_at": datetime.now(),
                        "progress_vnd": 0,
                        "buffer_vnd": 0,
                    }
                )
                st.session_state["saving_goals_flash"] = "Đã tạo mục tiêu tiết kiệm mẫu."
                st.rerun()

    st.subheader("Danh sách mục tiêu")
    goals = st.session_state["saving_goals_mock"]
    if not goals:
        st.info("Chưa có mục tiêu tiết kiệm. Hãy tạo mục tiêu đầu tiên ở phía trên.")
        return

    status_filter_labels = {"Tất cả": None, **GOAL_STATUS_LABELS}
    selected_label = st.selectbox(
        "Lọc theo trạng thái",
        list(status_filter_labels),
        key="saving_goals_status_filter",
    )
    selected_status = status_filter_labels[selected_label]
    filtered_goals = [
        goal
        for goal in goals
        if selected_status is None or goal["status"] == selected_status
    ]

    if filtered_goals:
        table = pd.DataFrame(
            [
                {
                    "Tên mục tiêu": goal["name"],
                    "Số tiền mục tiêu": format_vnd(goal["target_amount_vnd"]),
                    "Deadline": format_date(goal["deadline"]),
                    "Trạng thái": GOAL_STATUS_LABELS[goal["status"]],
                }
                for goal in filtered_goals
            ],
            index=[goal["goal_id"] for goal in filtered_goals],
        )
        table.index.name = "Mock goal_id"
        st.dataframe(table, use_container_width=True)

        st.subheader("Tiến độ mục tiêu")
        for goal in filtered_goals:
            target_amount_vnd = goal["target_amount_vnd"]
            progress_vnd = goal.get("progress_vnd", 0)
            buffer_vnd = goal.get("buffer_vnd", 0)
            remaining_vnd = max(target_amount_vnd - progress_vnd, 0)
            completion_percentage = progress_vnd / target_amount_vnd * 100
            progress_bar_value = min(max(completion_percentage, 0), 100)

            with st.container(border=True):
                st.markdown(f"**{goal['name']}**")
                target_col, progress_col, remaining_col = st.columns(3)
                target_col.metric("Số tiền mục tiêu", format_vnd(target_amount_vnd))
                progress_col.metric("Đã tích lũy", format_vnd(progress_vnd))
                remaining_col.metric("Còn thiếu", format_vnd(remaining_vnd))

                percentage_col, buffer_col = st.columns(2)
                percentage_col.metric(
                    "Hoàn thành", f"{completion_percentage:.1f}%"
                )
                buffer_col.metric("Số dư dự phòng", format_vnd(buffer_vnd))
                st.progress(progress_bar_value / 100)
    else:
        st.info("Không có mục tiêu phù hợp với trạng thái đã chọn.")

    editable_goals = [goal for goal in goals if goal["status"] == "active"]
    if not editable_goals:
        return

    active_ids = [goal["goal_id"] for goal in editable_goals]
    selected_goal_id = st.selectbox(
        "Chọn mục tiêu đang thực hiện",
        active_ids,
        format_func=lambda goal_id: _find_goal(goal_id)["name"],
        key="saving_goal_action_" + "_".join(map(str, active_ids)),
    )
    selected_goal = _find_goal(selected_goal_id)
    if selected_goal is None:
        return

    with st.expander("Chỉnh sửa mục tiêu", expanded=False):
        st.caption("Chỉ có thể thay đổi số tiền mục tiêu và deadline; tên được giữ nguyên.")
        with st.form(f"edit_saving_goal_{selected_goal_id}"):
            edited_amount = st.number_input(
                "Số tiền mục tiêu (VND)",
                min_value=0,
                value=int(selected_goal["target_amount_vnd"]),
                step=100_000,
            )
            edited_deadline = st.date_input(
                "Deadline", value=selected_goal["deadline"]
            )
            save_edit = st.form_submit_button("Lưu thay đổi")

        if save_edit:
            if edited_amount <= 0:
                st.error("Số tiền mục tiêu phải lớn hơn 0 VND.")
            else:
                selected_goal["target_amount_vnd"] = int(edited_amount)
                selected_goal["deadline"] = edited_deadline
                st.session_state["saving_goals_flash"] = "Đã cập nhật mục tiêu mẫu."
                st.rerun()

    with st.expander("Hủy mục tiêu", expanded=False):
        st.warning("Mục tiêu đã hủy sẽ được giữ trong danh sách và không thể chỉnh sửa.")
        if st.button(
            "Hủy mục tiêu đang chọn",
            key=f"cancel_saving_goal_{selected_goal_id}",
            type="secondary",
        ):
            selected_goal["status"] = "cancelled"
            st.session_state["saving_goals_flash"] = "Đã hủy mục tiêu mẫu."
            st.rerun()
