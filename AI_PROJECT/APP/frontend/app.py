
import streamlit as st

from frontend.api_client import login, register
from frontend.user_state import get_display_name, get_user_id, set_user

from views.dashboard import render_dashboard
from views.transactions import render_transactions
from views.ai_assistant import render_ai_assistant
from views.budget import render_budget
from views.saving_goals import render_saving_goals


# 1. Cấu hình trang
st.set_page_config(
    page_title="AI Expense Assistant",
    page_icon="💰",
    layout="wide"
)

# 2. Tiêu đề ứng dụng
st.title(" AI Expense Assistant")
st.caption("Trợ lý quản lý chi tiêu thông minh dành cho sinh viên")

# 3. Thanh điều hướng bên trái
with st.sidebar:
    st.title("Menu")
    if get_user_id() is not None:
        st.caption(f"Đang đăng nhập: {get_display_name() or 'Người dùng'}")
        if st.button("Đăng xuất", use_container_width=True):
            set_user(None)
            st.rerun()
    selected_page = st.radio(
        "Điều hướng",
        ["Dashboard", "Transactions", "AI Assistant", "Budget", "Saving Goals"]
    )

if get_user_id() is None:
    st.info("Đăng nhập hoặc tạo tài khoản để kết nối dữ liệu với backend.")
    login_tab, register_tab = st.tabs(["Đăng nhập", "Tạo tài khoản"])
    with login_tab:
        with st.form("login_form", clear_on_submit=True):
            username = st.text_input("Tên đăng nhập")
            password = st.text_input("Mật khẩu", type="password")
            login_submitted = st.form_submit_button("Đăng nhập")
        if login_submitted:
            try:
                with st.spinner("Đang xác thực..."):
                    login(username, password)
                st.success("Đăng nhập thành công.")
                st.rerun()
            except Exception as error:
                st.error(f"Không thể đăng nhập: {error}")
    with register_tab:
        with st.form("register_form", clear_on_submit=True):
            display_name = st.text_input("Tên hiển thị")
            new_username = st.text_input("Tên đăng nhập", key="register_username")
            new_password = st.text_input(
                "Mật khẩu (ít nhất 8 ký tự)", type="password", key="register_password"
            )
            register_submitted = st.form_submit_button("Tạo tài khoản")
        if register_submitted:
            try:
                with st.spinner("Đang tạo tài khoản..."):
                    register(new_username, new_password, display_name)
                st.success("Tạo tài khoản thành công.")
                st.rerun()
            except Exception as error:
                st.error(f"Không thể tạo tài khoản: {error}")
    st.stop()

# 4. Nội dung chính
if selected_page == "Dashboard":
    render_dashboard()

elif selected_page == "Transactions":
    render_transactions()

elif selected_page == "AI Assistant":
    render_ai_assistant()

elif selected_page == "Budget":
    render_budget()

elif selected_page == "Saving Goals":
    render_saving_goals()
