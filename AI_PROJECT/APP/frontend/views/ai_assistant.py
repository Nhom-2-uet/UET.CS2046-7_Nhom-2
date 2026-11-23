from datetime import date

import pandas as pd
import streamlit as st

from frontend.api_client import request
from utils.formatting import format_date, format_vnd


def _as_dict(transaction) -> dict:
    if hasattr(transaction, "model_dump"):
        return transaction.model_dump()
    return dict(transaction)


def render_ai_assistant() -> None:
    st.header("Trợ lý AI")
    transaction_tab, question_tab = st.tabs(["Ghi giao dịch bằng AI", "Hỏi đáp chi tiêu"])

    with transaction_tab:
        st.caption("Gemini phân tích nội dung, bạn xem lại rồi xác nhận trước khi lưu.")
        text = st.text_area(
            "Nội dung giao dịch",
            placeholder="Sáng ăn phở 45k, trưa mua sách 120k, mẹ chuyển khoản 2 triệu",
            key="ai_transaction_input",
        )
        if st.button("Phân tích giao dịch", key="analyze_transactions"):
            if not text.strip():
                st.warning("Vui lòng nhập nội dung giao dịch trước khi phân tích.")
                st.session_state["ai_transaction_result"] = None
            else:
                try:
                    with st.spinner("Gemini đang phân tích..."):
                        result = request("ai.extract", {"text": text})
                    st.session_state["ai_transaction_result"] = [
                        _as_dict(item) for item in result.transactions
                    ]
                except Exception as error:
                    st.error(f"Không phân tích được nội dung: {error}")

        rows = st.session_state.get("ai_transaction_result")
        if rows:
            frame = pd.DataFrame(rows)
            frame["date"] = frame["date"].fillna(date.today().isoformat())
            frame["date"] = frame["date"].map(date.fromisoformat)
            frame["Số tiền"] = frame["amount"].map(format_vnd)
            frame["Ngày"] = frame["date"].map(format_date)
            frame["Loại"] = frame["type"].map({"income": "Thu nhập", "expense": "Chi tiêu"})
            st.dataframe(
                frame[["Ngày", "description", "category", "Loại", "Số tiền"]].rename(
                    columns={"description": "Mô tả", "category": "Danh mục"}
                ),
                hide_index=True,
                use_container_width=True,
            )
            if st.button("Xác nhận và lưu giao dịch", type="primary"):
                failures = []
                with st.spinner("Đang lưu giao dịch..."):
                    for index, row in enumerate(rows, start=1):
                        try:
                            request("transaction.create", {
                                "amount_vnd": int(row["amount"]),
                                "category_name": row["category"],
                                "transaction_type": row["type"],
                                "description": row["description"],
                                "transaction_date": date.fromisoformat(
                                    row.get("date") or date.today().isoformat()
                                ),
                                "input_source": "natural_language",
                            })
                        except Exception as error:
                            failures.append(f"Giao dịch {index}: {error}")
                if failures:
                    st.error("Một số giao dịch chưa lưu được: " + "; ".join(failures))
                else:
                    st.success(f"Đã lưu {len(rows)} giao dịch.")
                    st.session_state["ai_transaction_result"] = None
                    st.rerun()

    with question_tab:
        st.caption("Câu trả lời dùng số liệu giao dịch và ngân sách của tài khoản này.")
        question = st.text_area(
            "Câu hỏi của bạn",
            placeholder="Ví dụ: Tháng này tôi đã chi bao nhiêu?",
            key="ai_question_input",
        )
        if st.button("Gửi câu hỏi", key="send_finance_question"):
            if not question.strip():
                st.warning("Vui lòng nhập câu hỏi trước khi gửi.")
                st.session_state["ai_answer"] = None
            else:
                try:
                    with st.spinner("Đang tổng hợp số liệu và hỏi Gemini..."):
                        answer = request("finance.ask", {"question": question.strip()})
                    st.session_state["ai_last_question"] = question.strip()
                    st.session_state["ai_answer"] = answer
                except Exception as error:
                    st.error(f"Không lấy được câu trả lời: {error}")
        if st.session_state.get("ai_answer"):
            st.markdown(f"**Bạn hỏi:** {st.session_state.get('ai_last_question', '')}")
            st.info(st.session_state["ai_answer"])
