import streamlit as st


def render_budget() -> None:
    """Render the Budget page structure with placeholders for later milestones."""
    st.header("Quản lý ngân sách")
    st.caption("Theo dõi ngân sách, chi tiêu theo danh mục và các khoản chi bắt buộc.")

    with st.container(border=True):
        st.subheader("Thiết lập ngân sách")
        st.info("Khu vực thiết lập ngân sách sẽ được triển khai ở milestone tiếp theo.")

    with st.container(border=True):
        st.subheader("Tổng quan ngân sách")
        st.info("Khu vực tổng quan ngân sách sẽ được triển khai ở milestone tiếp theo.")

    with st.container(border=True):
        st.subheader("Chi tiêu theo danh mục")
        st.info("Khu vực chi tiêu theo danh mục sẽ được triển khai ở milestone tiếp theo.")

    with st.container(border=True):
        st.subheader("Khoản chi bắt buộc")
        st.info("Khu vực khoản chi bắt buộc sẽ được triển khai ở milestone tiếp theo.")
