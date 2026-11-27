"""Account overview rendered from the authenticated Streamlit session."""

from collections.abc import Callable
from html import escape

import streamlit as st

from frontend.components.design_system import (
    render_empty_state,
    render_page_header,
    section_container,
)
from frontend.user_state import get_display_name, get_user_id


_ACCOUNT_STYLES = """
<style>
.account-profile { display:flex; align-items:center; gap:1rem; padding:.35rem 0; }
.account-avatar { display:grid; flex:0 0 3.6rem; width:3.6rem; height:3.6rem; place-items:center; border-radius:1.15rem; background:linear-gradient(145deg,#3984e8,#2563eb); color:#fff; font-size:1.3rem; font-weight:750; box-shadow:0 8px 20px rgba(57,132,232,.2); }
.account-name { color:#202938; font-size:1.2rem; font-weight:750; overflow-wrap:anywhere; }
.account-role { margin-top:.18rem; color:#8491a3; font-size:.82rem; }
.account-section-title { margin:0 0 .2rem; color:#202938; font-size:1.05rem; font-weight:730; }
.account-section-caption { margin:0 0 .75rem; color:#8491a3; font-size:.83rem; }
.account-field-label { color:#8491a3; font-size:.75rem; font-weight:650; }
.account-field-value { margin-top:.2rem; color:#202938; font-size:.94rem; font-weight:650; overflow-wrap:anywhere; }
.account-note { padding:.75rem .85rem; border:1px solid #e6edf6; border-radius:.8rem; background:#f8faff; color:#64748b; font-size:.82rem; line-height:1.5; }
.account-security-mark { display:grid; width:2.35rem; height:2.35rem; place-items:center; border-radius:.75rem; background:#eef5ff; color:#3984e8; font-size:1rem; font-weight:750; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color:#e7edf5; border-radius:15px; background:#fff; box-shadow:0 4px 16px rgba(34,63,100,.045); }
@media(max-width:700px) { .account-profile { align-items:flex-start; } .account-name { font-size:1.05rem; } }
</style>
"""


def render_account(on_logout: Callable[[], None]) -> None:
    """Show available session profile information and existing account actions."""
    st.markdown(_ACCOUNT_STYLES, unsafe_allow_html=True)
    render_page_header("Account", "Thông tin tài khoản và trạng thái các tùy chọn cá nhân.")

    display_name = get_display_name()
    user_id = get_user_id()
    if not display_name and user_id is None:
        render_empty_state("Chưa có thông tin tài khoản trong phiên đăng nhập này.")
        return

    profile_col, action_col = st.columns([3, 1], vertical_alignment="center")
    with profile_col:
        with section_container():
            st.markdown(
                '<div class="account-profile"><div class="account-avatar">'
                f'{escape((display_name or "U")[:1].upper())}</div><div>'
                f'<div class="account-name">{escape(display_name or "Người dùng")}</div>'
                '<div class="account-role">Tài khoản đang đăng nhập</div></div></div>',
                unsafe_allow_html=True,
            )
            st.markdown('<div class="account-section-caption">Thông tin có trong phiên hiện tại</div>', unsafe_allow_html=True)
            detail_left, detail_right = st.columns(2)
            with detail_left:
                st.markdown('<div class="account-field-label">Tên hiển thị</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="account-field-value">{escape(display_name or "Chưa có thông tin")}</div>',
                    unsafe_allow_html=True,
                )
            with detail_right:
                st.markdown('<div class="account-field-label">ID tài khoản</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="account-field-value">{escape(str(user_id) if user_id is not None else "Chưa có thông tin")}</div>',
                    unsafe_allow_html=True,
                )
    with action_col:
        st.write("")
        if st.button("Đăng xuất", type="primary", use_container_width=True, key="account_logout"):
            on_logout()

    st.markdown('<div class="account-section-title">Hồ sơ cá nhân</div>', unsafe_allow_html=True)
    st.markdown('<div class="account-section-caption">Chỉ hiển thị thông tin đã được cung cấp trong phiên đăng nhập.</div>', unsafe_allow_html=True)
    with section_container():
        if not display_name:
            render_empty_state("Phiên đăng nhập chưa có tên hiển thị.")
        else:
            name_col, username_col = st.columns(2)
            with name_col:
                st.markdown('<div class="account-field-label">Tên hiển thị</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="account-field-value">{escape(display_name)}</div>', unsafe_allow_html=True)
            with username_col:
                st.markdown('<div class="account-field-label">Email / tên đăng nhập</div>', unsafe_allow_html=True)
                st.markdown('<div class="account-field-value">Chưa có trong session</div>', unsafe_allow_html=True)
            st.markdown('<div class="account-note">Cập nhật hồ sơ chưa khả dụng: ứng dụng chưa có API đọc hoặc lưu thông tin cá nhân.</div>', unsafe_allow_html=True)

    st.markdown('<div class="account-section-title">Bảo mật</div>', unsafe_allow_html=True)
    st.markdown('<div class="account-section-caption">Thông tin đăng nhập được giữ riêng tư trong phiên ứng dụng.</div>', unsafe_allow_html=True)
    with section_container():
        st.markdown(
            '<div style="display:flex;align-items:center;gap:.7rem;margin-bottom:.65rem">'
            '<span class="account-security-mark">✓</span><strong style="color:#202938">Phiên đăng nhập đang hoạt động</strong></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="account-note">Đổi mật khẩu và quản lý phương thức bảo mật chưa được backend hỗ trợ. Mật khẩu và token không được hiển thị tại đây.</div>', unsafe_allow_html=True)

    st.markdown('<div class="account-section-title">Tùy chọn</div>', unsafe_allow_html=True)
    with section_container():
        render_empty_state("Chưa có cài đặt tài khoản hoặc tùy chọn cá nhân được tích hợp.")
