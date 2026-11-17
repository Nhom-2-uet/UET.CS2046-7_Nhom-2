
import streamlit as st

from views.dashboard import render_dashboard
from views.transactions import render_transactions
from views.ai_assistant import render_ai_assistant
from views.budget import render_budget


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
    st.header("Mục tiêu tiết kiệm")
    st.write("Theo dõi các mục tiêu tiết kiệm.")
