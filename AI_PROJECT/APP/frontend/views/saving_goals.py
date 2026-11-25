import pandas as pd
import streamlit as st

from frontend.api_client import request
from utils.formatting import format_date, format_vnd


GOAL_STATUS_LABELS = {
    "active": "Đang thực hiện",
    "finished": "Hoàn thành",
    "failed": "Không đạt",
    "cancelled": "Đã hủy",
}


def render_saving_goals() -> None:
    st.header("Mục tiêu tiết kiệm")
    st.caption("Mục tiêu được lưu trong database và thuộc tài khoản đang đăng nhập.")
    try:
        with st.spinner("Đang tải mục tiêu..."):
            goals = request("goal.list")
    except Exception as error:
        st.error(f"Không tải được mục tiêu: {error}")
        return

    active_goals = [goal for goal in goals if goal.status == "active"]
    with st.container(border=True):
        st.subheader("Tạo mục tiêu tiết kiệm")
        if active_goals:
            st.info("Bạn đã có mục tiêu đang thực hiện. Hãy kết thúc mục tiêu đó trước.")
        with st.form("saving_goal_create_form", clear_on_submit=True):
            name = st.text_input("Tên mục tiêu", max_chars=150)
            target = st.number_input("Số tiền mục tiêu (VND)", min_value=1, step=100_000)
            deadline = st.date_input("Hạn hoàn thành")
            create = st.form_submit_button("Tạo mục tiêu", disabled=bool(active_goals))
        if create:
            if target <= 0:
                st.error("Số tiền mục tiêu phải lớn hơn 0 VND.")
            else:
                try:
                    with st.spinner("Đang tạo mục tiêu..."):
                        request("goal.create", {
                            "name": name, "target_amount_vnd": int(target), "deadline": deadline
                        })
                    st.success("Đã tạo mục tiêu.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Không thể tạo mục tiêu: {error}")

    st.subheader("Danh sách mục tiêu")
    if not goals:
        st.info("Chưa có mục tiêu tiết kiệm.")
        return
    selected_label = st.selectbox("Lọc trạng thái", ["Tất cả", *GOAL_STATUS_LABELS.values()])
    status_by_label = {label: status for status, label in GOAL_STATUS_LABELS.items()}
    visible = [
        goal for goal in goals
        if selected_label == "Tất cả" or goal.status == status_by_label[selected_label]
    ]
    table = pd.DataFrame([
        {
            "Tên mục tiêu": goal.name,
            "Mục tiêu": format_vnd(goal.target_amount_vnd),
            "Đã tích lũy": format_vnd(goal.progress_vnd),
            "Còn thiếu": format_vnd(max(goal.target_amount_vnd - goal.progress_vnd, 0)),
            "Deadline": format_date(goal.deadline),
            "Trạng thái": GOAL_STATUS_LABELS[goal.status],
        }
        for goal in visible
    ])
    st.dataframe(table, hide_index=True, use_container_width=True)

    editable = [goal for goal in goals if goal.status == "active"]
    if not editable:
        return
    selected = st.selectbox(
        "Chọn mục tiêu đang thực hiện", editable,
        format_func=lambda goal: goal.name,
    )
    with st.expander("Chỉnh sửa số tiền và deadline"):
        with st.form(f"edit_goal_{selected.goal_id}"):
            target = st.number_input(
                "Số tiền mục tiêu (VND)", min_value=1,
                value=int(selected.target_amount_vnd), step=100_000,
            )
            deadline = st.date_input("Deadline", value=selected.deadline)
            save = st.form_submit_button("Lưu thay đổi")
        if save:
            if target <= 0:
                st.error("Số tiền mục tiêu phải lớn hơn 0 VND.")
            else:
                try:
                    result = request("goal.update", {
                        "goal_id": selected.goal_id,
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
    if st.button("Hủy mục tiêu", key=f"cancel_goal_{selected.goal_id}"):
        try:
            result = request("goal.cancel", {"goal_id": selected.goal_id})
            if result is None:
                st.error("Không tìm thấy mục tiêu để hủy.")
            else:
                st.success("Đã hủy mục tiêu.")
                st.rerun()
        except Exception as error:
            st.error(f"Không thể hủy mục tiêu: {error}")
