"""Streamlit entry point for AI Expense Assistant."""

import sys
from pathlib import Path

import streamlit as st

# The app can be started from APP/main.py (cwd=frontend) or directly by Streamlit.
APP_DIR = Path(__file__).resolve().parents[1]
AI_PROJECT_DIR = APP_DIR.parent
for import_path in (str(APP_DIR), str(AI_PROJECT_DIR)):
    if import_path not in sys.path:
        sys.path.insert(0, import_path)

from frontend.api_client import login, register
from frontend.components.design_system import (
    apply_design_system,
    render_brand,
    render_empty_state,
    render_page_header,
    section_container,
)
from frontend.user_state import get_display_name, get_user_id, set_user
from views.dashboard import render_dashboard
from views.transactions import render_transactions
from views.ai_assistant import render_ai_assistant
from views.budget import render_budget
from views.saving_goals import render_saving_goals


st.set_page_config(
    page_title="AI Expense Assistant",
    page_icon="💰",
    layout="wide",
)
apply_design_system()

st.title("AI Expense Assistant")
st.caption("Trợ lý quản lý chi tiêu thông minh dành cho sinh viên")

if get_user_id() is None:
    st.subheader("Đăng nhập để sử dụng ứng dụng")
    login_tab, register_tab = st.tabs(["Đăng nhập", "Tạo tài khoản"])

    with login_tab:
        with st.form("login_form", clear_on_submit=True):
            username = st.text_input("Tên đăng nhập")
            password = st.text_input("Mật khẩu", type="password")
            submitted = st.form_submit_button("Đăng nhập")
        if submitted:
            try:
                with st.spinner("Đang xác thực..."):
                    login(username, password)
                st.success("Đăng nhập thành công.")
                st.rerun()
            except Exception as error:
                st.error(f"Không thể đăng nhập: {error}")

    with register_tab:
        with st.form("register_form", clear_on_submit=True):
            display_name = st.text_input("Tên hiển thị", max_chars=100)
            new_username = st.text_input("Tên đăng nhập", max_chars=100)
            new_password = st.text_input(
                "Mật khẩu (ít nhất 8 ký tự)", type="password"
            )
            confirm_password = st.text_input("Nhập lại mật khẩu", type="password")
            submitted = st.form_submit_button("Tạo tài khoản")
        if submitted:
            if new_password != confirm_password:
                st.error("Hai mật khẩu chưa khớp.")
            else:
                try:
                    with st.spinner("Đang tạo tài khoản..."):
                        register(new_username, new_password, display_name)
                    st.success("Tạo tài khoản thành công.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Không thể tạo tài khoản: {error}")

    st.info("Cần kết nối MySQL và tạo database theo database/schema.sql trước.")
    st.stop()

with st.sidebar:
    render_brand()
    st.caption(f"Đang đăng nhập: {get_display_name() or 'Người dùng'}")
    if st.button("Đăng xuất", use_container_width=True):
        set_user(None)
        for key in list(st.session_state):
            if key.startswith("ai_"):
                del st.session_state[key]
        st.session_state.pop("app_page", None)
        st.rerun()
    st.markdown("---")
    st.caption("ĐIỀU HƯỚNG")
    selected_page = st.radio(
        "Điều hướng",
        ["AI Chat", "Dashboard", "Transactions", "Budget", "Saving Goals", "Account"],
        index=0,
        key="app_page",
    )

if selected_page == "AI Chat":
    render_ai_assistant()
elif selected_page == "Dashboard":
    render_dashboard()
elif selected_page == "Transactions":
    render_transactions()
elif selected_page == "Budget":
    render_budget()
elif selected_page == "Saving Goals":
    render_saving_goals()
else:
    render_page_header("Account", "Thông tin và cài đặt tài khoản.")
    with section_container():
        st.subheader("Tính năng đang được phát triển")
        render_empty_state(
            "Trang tài khoản chưa được tích hợp với backend. "
            "Các thao tác hồ sơ sẽ xuất hiện khi có command hỗ trợ."
        )
