from datetime import date

import pandas as pd
import streamlit as st

from utils.formatting import format_date, format_vnd


QA_SUGGESTIONS = [
    "Tháng này tôi đã chi bao nhiêu?",
    "Danh mục nào tôi chi nhiều nhất?",
    "So sánh chi tiêu tháng này với tháng trước.",
]


def _mock_transaction_result() -> list[dict]:
    """Return illustrative records for the UI demo; does not parse user input."""
    today = date.today()
    return [
        {
            "Ngày": today,
            "Tên giao dịch": "Ăn phở",
            "Danh mục": "Ăn uống",
            "Loại giao dịch": "Chi tiêu",
            "Số tiền": 45_000,
        },
        {
            "Ngày": today,
            "Tên giao dịch": "Mua sách",
            "Danh mục": "Học tập",
            "Loại giao dịch": "Chi tiêu",
            "Số tiền": 120_000,
        },
        {
            "Ngày": today,
            "Tên giao dịch": "Mẹ chuyển khoản",
            "Danh mục": "Gia đình gửi",
            "Loại giao dịch": "Thu nhập",
            "Số tiền": 2_000_000,
        },
    ]


def _mock_answer(question: str) -> str:
    """Return a fixed illustrative answer for common demo questions."""
    answers = {
        QA_SUGGESTIONS[0]: (
            "Theo dữ liệu minh họa, tổng chi tiêu tháng này là 2.500.000 đ."
        ),
        QA_SUGGESTIONS[1]: (
            "Theo dữ liệu minh họa, Ăn uống là danh mục chi nhiều nhất "
            "với 1.000.000 đ."
        ),
        QA_SUGGESTIONS[2]: (
            "Theo dữ liệu minh họa, tháng này bạn chi 2.500.000 đ, "
            "tháng trước chi 2.100.000 đ. Chi tiêu tăng khoảng 19%."
        ),
    }
    return answers.get(
        question.strip(),
        "Đây là câu trả lời mô phỏng. Ứng dụng chưa truy vấn dữ liệu "
        "giao dịch hoặc phân tích câu hỏi bằng AI.",
    )


def render_ai_assistant() -> None:
    """Render the AI Assistant UI using session-local mock responses."""
    st.header("Trợ lý AI")
    transaction_tab, question_tab = st.tabs(
        ["Ghi giao dịch bằng AI", "Hỏi đáp chi tiêu"]
    )

    st.session_state.setdefault("ai_transaction_input", "")
    st.session_state.setdefault("ai_transaction_result", None)
    st.session_state.setdefault("ai_question_input", "")
    st.session_state.setdefault("ai_last_question", "")
    st.session_state.setdefault("ai_mock_answer", None)

    with transaction_tab:
        st.subheader("Ghi giao dịch bằng AI")
        st.caption(
            "Nhập các khoản thu chi bằng ngôn ngữ tự nhiên để xem kết quả mẫu."
        )
        st.text_area(
            "Nội dung giao dịch",
            placeholder=(
                "Sáng ăn phở 45k, trưa mua sách 120k, "
                "mẹ chuyển khoản 2 triệu"
            ),
            key="ai_transaction_input",
        )

        if st.button("Phân tích giao dịch", key="analyze_mock_transactions"):
            if st.session_state.ai_transaction_input.strip():
                st.session_state.ai_transaction_result = (
                    _mock_transaction_result()
                )
            else:
                st.session_state.ai_transaction_result = None
                st.warning("Vui lòng nhập nội dung giao dịch trước khi phân tích.")

        if st.session_state.ai_transaction_result is not None:
            st.info(
                "Đây là kết quả mô phỏng bằng dữ liệu mẫu, chưa phải kết quả "
                "phân tích từ Gemini."
            )
            result_table = pd.DataFrame(st.session_state.ai_transaction_result)
            result_table["Ngày"] = result_table["Ngày"].map(format_date)
            result_table["Số tiền"] = result_table["Số tiền"].map(format_vnd)
            st.dataframe(result_table, hide_index=True, use_container_width=True)

    with question_tab:
        st.subheader("Hỏi đáp chi tiêu")
        st.caption("Đặt câu hỏi về thu chi hoặc chọn một câu hỏi gợi ý.")

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

        if st.button("Gửi câu hỏi", key="send_mock_question"):
            question = st.session_state.ai_question_input.strip()
            if question:
                st.session_state.ai_last_question = question
                st.session_state.ai_mock_answer = _mock_answer(question)
            else:
                st.session_state.ai_last_question = ""
                st.session_state.ai_mock_answer = None
                st.warning("Vui lòng nhập câu hỏi trước khi gửi.")

        if st.session_state.ai_mock_answer is not None:
            st.markdown(f"**Bạn hỏi:** {st.session_state.ai_last_question}")
            st.info(st.session_state.ai_mock_answer)
            st.caption(
                "Số liệu trong câu trả lời chỉ để minh họa, chưa lấy từ Database."
            )
