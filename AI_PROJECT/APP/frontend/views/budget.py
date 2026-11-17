import streamlit as st

from utils.formatting import format_vnd


def render_budget() -> None:
    """Render the Budget page with a session-local monthly budget form."""
    st.header("Quản lý ngân sách")
    st.caption("Theo dõi ngân sách, chi tiêu theo danh mục và các khoản chi bắt buộc.")

    st.session_state.setdefault("budget_settings_mock", None)
    st.session_state.setdefault("budget_monthly_input", 0)
    st.session_state.setdefault("budget_payday_input", 1)

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
        st.info("Khu vực tổng quan ngân sách sẽ được triển khai ở milestone tiếp theo.")

    with st.container(border=True):
        st.subheader("Chi tiêu theo danh mục")
        st.info("Khu vực chi tiêu theo danh mục sẽ được triển khai ở milestone tiếp theo.")

    with st.container(border=True):
        st.subheader("Khoản chi bắt buộc")
        st.info("Khu vực khoản chi bắt buộc sẽ được triển khai ở milestone tiếp theo.")
