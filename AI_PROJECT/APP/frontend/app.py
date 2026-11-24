
import sys
from pathlib import Path

import streamlit as st


APP_DIR = Path(__file__).resolve().parents[1]
AI_PROJECT_DIR = APP_DIR.parent
for import_path in (str(APP_DIR), str(AI_PROJECT_DIR)):
    if import_path not in sys.path:
        sys.path.insert(0, import_path)

from views.dashboard import render_dashboard
from views.transactions import render_transactions
from views.ai_assistant import render_ai_assistant
from views.budget import render_budget
from views.saving_goals import render_saving_goals
from APP.services.user_service import authenticate_user, create_user


# 1. Cấu hình trang
st.set_page_config(
    page_title="AI Expense Assistant",
    page_icon="💰",
    layout="wide"
)

# 2. Tiêu đề ứng dụng
st.title(" AI Expense Assistant")
st.caption("Trợ lý quản lý chi tiêu thông minh dành cho sinh viên")

if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

if st.session_state.authenticated_user is None:
    st.subheader("Đăng nhập để sử dụng ứng dụng")
    login_tab, register_tab = st.tabs(["Đăng nhập", "Tạo tài khoản"])

    with login_tab:
        with st.form("login_form"):
            login_username = st.text_input("Tên đăng nhập")
            login_password = st.text_input("Mật khẩu", type="password")
            login_submitted = st.form_submit_button("Đăng nhập")

        if login_submitted:
            try:
                user = authenticate_user(login_username, login_password)
                if user is None:
                    st.error("Tên đăng nhập hoặc mật khẩu không đúng.")
                else:
                    st.session_state.authenticated_user = {
                        "user_id": user.user_id,
                        "display_name": user.display_name,
                    }
                    st.rerun()
            except Exception as error:
                st.error(f"Không đăng nhập được: {error}")

    with register_tab:
        with st.form("register_form"):
            register_name = st.text_input("Tên hiển thị", max_chars=100)
            register_username = st.text_input("Tên đăng nhập", max_chars=100)
            register_password = st.text_input(
                "Mật khẩu (ít nhất 8 ký tự)", type="password"
            )
            register_password_confirm = st.text_input(
                "Nhập lại mật khẩu", type="password"
            )
            register_submitted = st.form_submit_button("Tạo tài khoản")

        if register_submitted:
            if register_password != register_password_confirm:
                st.error("Hai mật khẩu chưa khớp.")
            else:
                try:
                    user = create_user(
                        username=register_username,
                        password=register_password,
                        display_name=register_name,
                    )
                    st.session_state.authenticated_user = {
                        "user_id": user.user_id,
                        "display_name": user.display_name,
                    }
                    st.success("Tạo tài khoản thành công.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Không tạo được tài khoản: {error}")

    st.info("Cần kết nối MySQL và tạo database theo database/schema.sql trước.")
    st.stop()

# 3. Thanh điều hướng bên trái
with st.sidebar:
    st.title("Menu")
    st.write(f"Xin chào, {st.session_state.authenticated_user['display_name']}")
    if st.button("Đăng xuất"):
        st.session_state.authenticated_user = None
        for state_key in list(st.session_state):
            if state_key.startswith("ai_"):
                del st.session_state[state_key]
        st.rerun()
    selected_page = st.radio(
        "Điều hướng",
        ["Dashboard", "Transactions", "AI Assistant", "Budget", "Saving Goals"]
    )

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
