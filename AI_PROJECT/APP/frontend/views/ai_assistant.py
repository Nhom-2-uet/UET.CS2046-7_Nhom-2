import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from utils.formatting import format_date, format_vnd


# Streamlit starts with the frontend directory on sys.path. Add AI_PROJECT so
# this view can import the existing Gemini service and its prompt/schema.
AI_PROJECT_DIR = Path(__file__).resolve().parents[3]
APP_DIR = AI_PROJECT_DIR / "APP"
for import_path in (str(APP_DIR), str(AI_PROJECT_DIR)):
    if import_path not in sys.path:
        sys.path.insert(0, import_path)


QA_SUGGESTIONS = [
    "Tháng này tôi đã chi bao nhiêu?",
    "Danh mục nào tôi chi nhiều nhất?",
    "So sánh chi tiêu tháng này với tháng trước.",
]


def render_ai_assistant() -> None:
    """Render the AI Assistant UI."""
    st.header("Trợ lý AI")
    transaction_tab, question_tab = st.tabs(
        ["Ghi giao dịch bằng AI", "Hỏi đáp chi tiêu"]
    )

    st.session_state.setdefault("ai_transaction_input", "")
    st.session_state.setdefault("ai_transaction_result", None)
    st.session_state.setdefault("ai_transaction_error", None)
    st.session_state.setdefault("ai_transaction_saved", None)
    st.session_state.setdefault("ai_question_input", "")
    st.session_state.setdefault("ai_last_question", "")
    st.session_state.setdefault("ai_answer", None)
    st.session_state.setdefault("ai_answer_error", None)

    with transaction_tab:
        st.subheader("Ghi giao dịch bằng AI")
        st.caption("Gemini sẽ nhận diện các khoản thu chi trong câu bạn nhập.")
        st.text_area(
            "Nội dung giao dịch",
            placeholder=(
                "Sáng ăn phở 45k, trưa mua sách 120k, "
                "mẹ chuyển khoản 2 triệu"
            ),
            key="ai_transaction_input",
        )

        if st.button("Phân tích giao dịch", key="analyze_gemini_transactions"):
            user_input = st.session_state.ai_transaction_input.strip()
            for state_key in list(st.session_state):
                if state_key.startswith("ai_review_"):
                    del st.session_state[state_key]
            st.session_state.ai_transaction_result = None
            st.session_state.ai_transaction_error = None
            st.session_state.ai_transaction_saved = None
            if not user_input:
                st.session_state.ai_transaction_result = None
                st.warning("Vui lòng nhập nội dung giao dịch trước khi phân tích.")
            else:
                try:
                    # Import lazily so the rest of the UI can still open when
                    # Gemini dependencies or credentials are not configured.
                    from APP.services.ai_service import extract_with_gemini

                    with st.spinner("Đang phân tích giao dịch..."):
                        result = extract_with_gemini(user_input)
                    st.session_state.ai_transaction_result = [
                        transaction.model_dump()
                        for transaction in result.transactions
                    ]
                except Exception as error:
                    st.session_state.ai_transaction_error = str(error)

        if st.session_state.ai_transaction_error:
            st.error(
                "Không phân tích được giao dịch. Hệ thống đang quá tải! Vui lòng đợi trong giây lát hoặc kiểm tra lại kết nối mạng của bạn. "
                f"Chi tiết: {st.session_state.ai_transaction_error}"
            )

        if st.session_state.ai_transaction_result is not None:
            transactions = st.session_state.ai_transaction_result
            if not transactions:
                st.info("Gemini chưa nhận diện được giao dịch nào từ nội dung này.")
            else:
                st.success("Gemini đã nhận diện giao dịch. Hãy kiểm tra và sửa trước khi lưu:")
                try:
                    from APP.services.logic.transaction_flow_service import (
                        confirm_and_save_transactions,
                        get_transaction_categories,
                        prepare_transaction_draft,
                    )

                    category_options = {
                        transaction_type: get_transaction_categories(transaction_type)
                        for transaction_type in {
                            item["type"] for item in transactions
                        }
                    }
                    if any(not choices for choices in category_options.values()):
                        st.error(
                            "Database chưa có danh mục đang hoạt động cho loại "
                            "giao dịch này. Hãy kiểm tra database/schema.sql."
                        )
                    else:
                        reviewed = []
                        with st.form("ai_transaction_review_form"):
                            for index, item in enumerate(transactions):
                                st.markdown(f"**Giao dịch {index + 1}**")
                                type_labels = {"expense": "Chi tiêu", "income": "Thu nhập"}
                                type_values = {label: value for value, label in type_labels.items()}
                                current_type_label = type_labels.get(item["type"], "Chi tiêu")
                                type_label = st.selectbox(
                                    "Loại giao dịch",
                                    list(type_values),
                                    index=list(type_values).index(current_type_label),
                                    key=f"ai_review_type_{index}",
                                )
                                transaction_type = type_values[type_label]
                                choices = category_options.get(transaction_type)
                                if choices is None:
                                    choices = get_transaction_categories(transaction_type)
                                    category_options[transaction_type] = choices
                                if not choices:
                                    st.error(f"Không có danh mục cho loại {type_label.lower()}.")
                                    choices = ["Khác"]
                                category_index = (
                                    choices.index(item["category"])
                                    if item.get("category") in choices
                                    else 0
                                )
                                description_col, amount_col = st.columns(2)
                                with description_col:
                                    description = st.text_input(
                                        "Tên giao dịch",
                                        value=item.get("description", ""),
                                        max_chars=500,
                                        key=f"ai_review_description_{index}",
                                    )
                                with amount_col:
                                    amount = st.number_input(
                                        "Số tiền (VND)",
                                        min_value=1,
                                        value=max(int(item.get("amount", 1)), 1),
                                        step=1000,
                                        key=f"ai_review_amount_{index}",
                                    )
                                category_col, date_col = st.columns(2)
                                with category_col:
                                    category = st.selectbox(
                                        "Danh mục",
                                        choices,
                                        index=category_index,
                                        key=f"ai_review_category_{index}_{transaction_type}",
                                    )
                                with date_col:
                                    try:
                                        initial_date = date.fromisoformat(item.get("date") or "")
                                    except ValueError:
                                        initial_date = date.today()
                                    transaction_date = st.date_input(
                                        "Ngày giao dịch",
                                        value=initial_date,
                                        key=f"ai_review_date_{index}",
                                    )
                                reviewed.append(
                                    {
                                        "amount": int(amount),
                                        "category": category,
                                        "type": transaction_type,
                                        "description": description,
                                        "date": transaction_date.isoformat(),
                                    }
                                )
                                if index < len(transactions) - 1:
                                    st.divider()

                            confirmed = st.form_submit_button(
                                f"Xác nhận và lưu {len(transactions)} giao dịch"
                            )

                        if confirmed:
                            try:
                                drafts = [prepare_transaction_draft(item) for item in reviewed]
                                saved = confirm_and_save_transactions(
                                    user_id=st.session_state.authenticated_user["user_id"],
                                    drafts=drafts,
                                    confirmed=True,
                                )
                                st.session_state.ai_transaction_saved = [
                                    {
                                        "transaction_id": transaction.transaction_id,
                                        "date": transaction.transaction_date.isoformat(),
                                        "description": transaction.description,
                                        "category": transaction.category_name,
                                        "type": transaction.transaction_type,
                                        "amount": transaction.amount_vnd,
                                    }
                                    for transaction in saved
                                ]
                                st.session_state.ai_transaction_result = None
                                st.rerun()
                            except Exception as error:
                                st.error(f"Chưa lưu được giao dịch: {error}")

                    if any(item.get("date_is_default") for item in transactions):
                        st.caption(
                            "Ngày không được nêu trong câu nhập được đặt là hôm nay; "
                            "bạn có thể sửa trước khi lưu."
                        )
                except Exception as error:
                    st.error(
                        "Không tải được danh mục từ MySQL. Hãy kiểm tra kết nối "
                        f"database và cấu hình AI_PROJECT/.env. Chi tiết: {error}"
                    )

        if st.session_state.ai_transaction_saved:
            saved = st.session_state.ai_transaction_saved
            st.success(f"Đã lưu {len(saved)} giao dịch vào MySQL.")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Mã": item["transaction_id"],
                            "Ngày": format_date(date.fromisoformat(item["date"])),
                            "Tên giao dịch": item["description"],
                            "Danh mục": item["category"],
                            "Loại": "Thu nhập" if item["type"] == "income" else "Chi tiêu",
                            "Số tiền": format_vnd(item["amount"]),
                        }
                        for item in saved
                    ]
                ),
                hide_index=True,
                use_container_width=True,
            )

    with question_tab:
        st.subheader("Hỏi đáp chi tiêu")
        st.caption(
            "Gemini trả lời câu hỏi và đưa lời khuyên quản lý chi tiêu. "
            "Dữ liệu giao dịch cá nhân chưa được nối vào tab này."
        )

        suggestion_columns = st.columns(len(QA_SUGGESTIONS))
        for index, (column, suggestion) in enumerate(
            zip(suggestion_columns, QA_SUGGESTIONS)
        ):
            if column.button(
                suggestion,
                key=f"ai_question_suggestion_{index}",
                use_container_width=True,
            ):
                st.session_state.ai_question_input = suggestion

        st.text_area(
            "Câu hỏi của bạn",
            placeholder="Ví dụ: Tháng này tôi đã chi bao nhiêu?",
            key="ai_question_input",
        )

        if st.button("Gửi câu hỏi", key="send_ai_question"):
            question = st.session_state.ai_question_input.strip()
            if question:
                st.session_state.ai_last_question = question
                st.session_state.ai_answer = None
                st.session_state.ai_answer_error = None
                try:
                    from APP.services.ai_service import answer_finance_question

                    with st.spinner("Gemini đang suy nghĩ..."):
                        st.session_state.ai_answer = answer_finance_question(question)
                except Exception as error:
                    st.session_state.ai_answer_error = str(error)
            else:
                st.session_state.ai_last_question = ""
                st.session_state.ai_answer = None
                st.session_state.ai_answer_error = None
                st.warning("Vui lòng nhập câu hỏi trước khi gửi.")

        if st.session_state.ai_answer_error:
            error_message = st.session_state.ai_answer_error
            if "503" in error_message or "UNAVAILABLE" in error_message:
                st.error("Gemini đang quá tải. Vui lòng đợi một chút rồi thử lại.")
            elif "429" in error_message or "RESOURCE_EXHAUSTED" in error_message:
                st.error(
                    "Gemini đã hết hạn mức gọi API hiện tại. Hãy kiểm tra quota "
                    "hoặc thử lại sau."
                )
            else:
                st.error(
                    "Không gửi được câu hỏi tới Gemini. Kiểm tra cấu hình "
                    "GEMINI_API_KEY, GEMINI_MODEL trong AI_PROJECT/.env và "
                    f"kết nối mạng. Chi tiết: {error_message}"
                )

        if st.session_state.ai_answer is not None:
            st.markdown(f"**Bạn hỏi:** {st.session_state.ai_last_question}")
            st.info(st.session_state.ai_answer)
