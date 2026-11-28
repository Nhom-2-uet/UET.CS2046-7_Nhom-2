"""AI transaction capture and personal finance Q&A screens."""

from datetime import date
from html import escape

import pandas as pd
import streamlit as st

from frontend.api_client import request
from frontend.components.design_system import (
    render_empty_state,
    render_error_state,
    render_page_header,
    section_container,
)
from utils.formatting import format_date, format_vnd


TYPE_LABELS = {"expense": "Chi tiêu", "income": "Thu nhập"}
TYPE_VALUES = {label: value for value, label in TYPE_LABELS.items()}
QA_SUGGESTIONS = [
    "Tháng này tôi đã chi bao nhiêu?",
    "Danh mục nào tôi chi nhiều nhất?",
    "So sánh chi tiêu tháng này với tháng trước.",
    "Tôi nên làm gì để tối ưu chi tiêu tháng này?",
]

_AI_STYLES = """
<style>
.ai-status { display:flex; align-items:center; gap:.5rem; width:fit-content; margin:-.25rem 0 1.2rem; padding:.38rem .7rem; border:1px solid #dce9fb; border-radius:999px; background:#f1f7ff; color:#47617f; font-size:.76rem; font-weight:600; }
.ai-status-dot { width:.48rem; height:.48rem; border-radius:50%; background:#3984e8; box-shadow:0 0 0 3px #dceaff; }
.ai-section-title { margin:.2rem 0 .2rem; color:#202938; font-size:1.08rem; font-weight:730; }
.ai-section-caption { margin:0 0 .85rem; color:#8491a3; font-size:.84rem; }
.ai-welcome { padding:.45rem .1rem; }
.ai-welcome-icon { display:grid; width:2.8rem; height:2.8rem; margin-bottom:.75rem; place-items:center; border-radius:.9rem; background:#eef5ff; color:#3984e8; font-size:1.25rem; font-weight:750; }
.ai-message-label { margin-bottom:.35rem; color:#8491a3; font-size:.74rem; font-weight:700; letter-spacing:.04em; text-transform:uppercase; }
.ai-user-message { margin:.15rem 0 .8rem auto; max-width:88%; padding:.8rem 1rem; border:1px solid #dce9fb; border-radius:1rem 1rem .25rem 1rem; background:#eef5ff; color:#202938; overflow-wrap:anywhere; }
.ai-feature-chip { display:inline-flex; margin:0 .35rem .35rem 0; padding:.32rem .58rem; border:1px solid #e5edf7; border-radius:999px; background:#fff; color:#64748b; font-size:.72rem; font-weight:600; }
.ai-review-caption { margin:.25rem 0 .8rem; color:#8491a3; font-size:.84rem; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color:#e7edf5; border-radius:15px; background:#fff; box-shadow:0 4px 16px rgba(34,63,100,.045); }
button[kind="secondary"] { border-color:#e3eaf3; border-radius:10px; background:#fff; color:#34445b; }
button[kind="secondary"]:hover { border-color:#b9d4f8; color:#2563eb; }
[data-testid="stMetricLabel"] p { color:#8491a3; font-size:.8rem; font-weight:600; }
[data-testid="stMetricValue"] { color:#202938; font-size:clamp(1.05rem,1.8vw,1.4rem); }
@media(max-width:700px) { .ai-user-message { max-width:100%; } [data-testid="stMetricValue"] { font-size:1rem; } }
</style>
"""


def _as_dict(transaction) -> dict:
    if hasattr(transaction, "model_dump"):
        return transaction.model_dump()
    if isinstance(transaction, dict):
        return dict(transaction)
    return dict(transaction)


def _load_categories(transaction_type: str) -> list[str]:
    rows = request("transaction.categories", {"transaction_type": transaction_type})
    return [row["name"] if isinstance(row, dict) else str(row) for row in rows]


def render_ai_assistant() -> None:
    st.markdown(_AI_STYLES, unsafe_allow_html=True)
    render_page_header(
        "Trợ lý tài chính AI",
        "Hỏi về chi tiêu hoặc ghi nhận giao dịch bằng ngôn ngữ tự nhiên.",
    )
    st.markdown(
        '<div class="ai-status"><span class="ai-status-dot"></span>'
        'Phân tích theo dữ liệu tài khoản đang đăng nhập</div>',
        unsafe_allow_html=True,
    )
    question_tab, transaction_tab = st.tabs(
        ["Hỏi đáp tài chính", "Ghi giao dịch bằng AI"]
    )

    with transaction_tab:
        st.markdown('<div class="ai-section-title">Ghi nhận giao dịch bằng mô tả</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="ai-section-caption">AI trích xuất thông tin để bạn kiểm tra và xác nhận trước khi lưu.</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<span class="ai-feature-chip">Thu / chi</span>'
            '<span class="ai-feature-chip">Danh mục</span>'
            '<span class="ai-feature-chip">Ngày giao dịch</span>',
            unsafe_allow_html=True,
        )
        text = st.text_area(
            "Nội dung giao dịch",
            placeholder="Ví dụ: Sáng ăn phở 45k, trưa mua sách 120k, mẹ chuyển khoản 2 triệu",
            key="ai_transaction_input",
            height=120,
        )
        if st.button("Phân tích giao dịch", key="analyze_transactions", type="primary", use_container_width=True):
            if not text.strip():
                st.warning("Vui lòng nhập nội dung giao dịch trước khi phân tích.")
                st.session_state["ai_transaction_result"] = None
            else:
                try:
                    with st.spinner("Gemini đang phân tích..."):
                        result = request("ai.extract", {"text": text.strip()})
                    extracted = getattr(result, "transactions", None)
                    if extracted is None and isinstance(result, dict):
                        extracted = result.get("transactions", [])
                    st.session_state["ai_transaction_result"] = [
                        _as_dict(item) for item in (extracted or [])
                    ]
                    if not extracted:
                        st.warning("AI chưa nhận diện được giao dịch. Hãy thử mô tả rõ hơn.")
                except Exception as error:
                    st.error(f"Không phân tích được nội dung: {error}")

        rows = st.session_state.get("ai_transaction_result") or []
        if rows:
            st.markdown('<div class="ai-section-title">Kiểm tra và chỉnh sửa</div>', unsafe_allow_html=True)
            st.markdown('<div class="ai-review-caption">Chỉ những khoản bạn xác nhận mới được lưu.</div>', unsafe_allow_html=True)
            reviewed: list[dict] = []
            for index, row in enumerate(rows):
                with section_container():
                    st.markdown(f"#### Giao dịch {index + 1}")
                    raw_type = row.get("type", "expense")
                    if raw_type not in TYPE_VALUES.values():
                        raw_type = "expense"
                    selected_label = st.selectbox(
                        "Loại giao dịch",
                        list(TYPE_VALUES),
                        index=list(TYPE_VALUES.values()).index(raw_type),
                        key=f"ai_type_{index}",
                    )
                    transaction_type = TYPE_VALUES[selected_label]
                    try:
                        categories = _load_categories(transaction_type)
                    except Exception as error:
                        st.error(f"Không tải được danh mục: {error}")
                        categories = []
                    category = str(row.get("category") or "")
                    if category and category not in categories:
                        categories.append(category)
                    if not categories:
                        st.warning("Chưa có danh mục phù hợp trong MySQL.")
                        continue
                    default_category = category if category in categories else categories[0]
                    amount = st.number_input(
                        "Số tiền (VND)", min_value=1,
                        value=max(1, int(row.get("amount") or 1)), step=1000,
                        key=f"ai_amount_{index}",
                    )
                    description = st.text_input(
                        "Mô tả", value=str(row.get("description") or ""),
                        key=f"ai_description_{index}",
                    )
                    selected_category = st.selectbox(
                        "Danh mục", categories,
                        index=categories.index(default_category),
                        key=f"ai_category_{index}",
                    )
                    raw_date = row.get("date")
                    try:
                        transaction_date = date.fromisoformat(raw_date) if raw_date else date.today()
                    except (TypeError, ValueError):
                        transaction_date = date.today()
                    transaction_date = st.date_input(
                        "Ngày giao dịch", value=transaction_date,
                        key=f"ai_date_{index}",
                    )
                    reviewed.append({
                        "amount_vnd": int(amount),
                        "description": description.strip(),
                        "category_name": selected_category,
                        "transaction_type": transaction_type,
                        "transaction_date": transaction_date,
                        "input_source": "natural_language",
                    })

            if len(reviewed) == len(rows) and reviewed and st.button(
                "Xác nhận và lưu giao dịch", type="primary", key="confirm_ai_transactions", use_container_width=True
            ):
                if any(not item["description"] for item in reviewed):
                    st.error("Mỗi giao dịch cần có mô tả trước khi lưu.")
                else:
                    try:
                        with st.spinner("Đang lưu giao dịch vào MySQL..."):
                            saved = request("transaction.create_many", {"transactions": reviewed})
                        st.session_state["ai_transaction_saved"] = [
                            {
                                "transaction_id": item.transaction_id,
                                "transaction_date": item.transaction_date,
                                "description": item.description,
                                "category": item.category_name,
                                "type": item.transaction_type,
                                "amount": item.amount_vnd,
                            }
                            for item in saved
                        ]
                        st.session_state["ai_transaction_result"] = None
                        st.success(f"Đã lưu {len(saved)} giao dịch vào MySQL.")
                        st.rerun()
                    except Exception as error:
                        st.error(f"Chưa lưu được giao dịch: {error}")

        saved = st.session_state.get("ai_transaction_saved") or []
        if saved:
            st.success(f"Đã lưu {len(saved)} giao dịch vào MySQL.")
            display = pd.DataFrame([
                {
                    "Ngày": format_date(item["transaction_date"]),
                    "Mô tả": item["description"],
                    "Danh mục": item["category"],
                    "Loại": TYPE_LABELS.get(item["type"], item["type"]),
                    "Số tiền": format_vnd(item["amount"]),
                }
                for item in saved
            ])
            with section_container():
                st.dataframe(display, hide_index=True, use_container_width=True)

    with question_tab:
        st.markdown('<div class="ai-section-title">Trò chuyện về tài chính</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="ai-section-caption">Câu trả lời có thể sử dụng dữ liệu giao dịch của tài khoản đang đăng nhập.</div>',
            unsafe_allow_html=True,
        )
        with section_container():
            if not st.session_state.get("ai_answer"):
                st.markdown(
                    '<div class="ai-welcome"><div class="ai-welcome-icon">✦</div>'
                    '<strong>Bạn muốn tìm hiểu điều gì?</strong><br>'
                    '<span style="color:#8491a3;font-size:.86rem">Chọn câu hỏi gợi ý hoặc nhập câu hỏi của riêng bạn.</span></div>',
                    unsafe_allow_html=True,
                )
                for row in range(2):
                    prompt_columns = st.columns(2)
                    for index, (column, suggestion) in enumerate(
                        zip(prompt_columns, QA_SUGGESTIONS[row * 2:row * 2 + 2]),
                        start=row * 2,
                    ):
                        if column.button(
                            suggestion,
                            key=f"ai_question_suggestion_{index}",
                            use_container_width=True,
                        ):
                            st.session_state["ai_question_input"] = suggestion
            question = st.text_area(
                "Câu hỏi của bạn",
                placeholder="Ví dụ: Tháng này tôi đã chi bao nhiêu?",
                key="ai_question_input",
                height=95,
            )
            if st.button(
                "Gửi câu hỏi", key="send_finance_question", type="primary", use_container_width=True
            ):
                if not question.strip():
                    st.warning("Vui lòng nhập câu hỏi trước khi gửi.")
                    st.session_state["ai_answer"] = None
                else:
                    try:
                        with st.spinner("Đang tổng hợp số liệu và hỏi Gemini..."):
                            st.session_state["ai_answer"] = request(
                                "finance.ask", {"question": question.strip()}
                            )
                        st.session_state["ai_last_question"] = question.strip()
                    except Exception as error:
                        render_error_state(f"Không lấy được câu trả lời: {error}")
            if st.session_state.get("ai_answer"):
                st.markdown('<div class="ai-message-label">Bạn đã hỏi</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="ai-user-message">{escape(str(st.session_state.get("ai_last_question", "")))}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown('<div class="ai-message-label">Trợ lý tài chính</div>', unsafe_allow_html=True)
                result = st.session_state["ai_answer"]
                with section_container():
                    if isinstance(result, dict):
                        summary = result.get("summary", {})
                        if summary:
                            income_col, expense_col, remaining_col, category_col = st.columns(4)
                            income_col.metric("Thu tháng này", format_vnd(summary["income_vnd"]))
                            expense_col.metric("Chi tháng này", format_vnd(summary["expense_vnd"]))
                            remaining_value = summary.get("budget_remaining_vnd")
                            remaining_col.metric(
                                "Ngân sách còn lại",
                                format_vnd(remaining_value) if remaining_value is not None else "Chưa thiết lập",
                            )
                            category_col.metric(
                                "Chi nhiều nhất", summary.get("top_category") or "Chưa có dữ liệu",
                            )
                            if not summary.get("has_transactions"):
                                st.caption(
                                    "Bạn chưa ghi giao dịch trong tháng này; phần tư vấn "
                                    "theo lịch sử chi tiêu sẽ còn hạn chế."
                                )

                            purchase = summary.get("purchase_assessment")
                            if purchase:
                                st.caption(
                                    "Khoản tiền trong câu hỏi được hiểu là "
                                    f"{format_vnd(purchase['amount_vnd'])}."
                                )
                                if purchase.get("needs_amount_confirmation"):
                                    st.warning(
                                        "Số tiền được hiểu khá lớn; hãy kiểm tra lại "
                                        "cách ghi số và đơn vị trước khi dựa vào đánh giá này."
                                    )
                                if purchase.get("can_fit_monthly_plan") is True:
                                    st.success(
                                        "Theo ngân sách linh hoạt ước tính, khoản này "
                                        "có thể nằm trong hạn mức tháng."
                                    )
                                elif purchase.get("can_fit_monthly_plan") is False:
                                    st.warning(
                                        "Khoản này vượt ngân sách linh hoạt ước tính "
                                        "còn lại trong tháng."
                                    )
                                else:
                                    st.info(
                                        "Chưa thể kiểm tra khoản mua theo hạn mức vì "
                                        "bạn chưa thiết lập ngân sách tháng."
                                    )
                                st.caption(
                                    "Đây là ước tính theo ngân sách đã khai báo, không "
                                    "phải số dư tài khoản ngân hàng."
                                )
                        answer = result.get("answer", "")
                    else:
                        answer = str(result)
                    if answer:
                        st.markdown(answer)
                    else:
                        render_empty_state("Trợ lý chưa trả về nội dung câu trả lời.")
