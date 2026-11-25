"""AI transaction capture and personal finance Q&A screens."""

from datetime import date

import pandas as pd
import streamlit as st

from frontend.api_client import request
from utils.formatting import format_date, format_vnd


TYPE_LABELS = {"expense": "Chi tiêu", "income": "Thu nhập"}
TYPE_VALUES = {label: value for value, label in TYPE_LABELS.items()}
QA_SUGGESTIONS = [
    "Tháng này tôi đã chi bao nhiêu?",
    "Danh mục nào tôi chi nhiều nhất?",
    "So sánh chi tiêu tháng này với tháng trước.",
    "Tôi nên làm gì để tối ưu chi tiêu tháng này?",
]


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
    st.header("Trợ lý AI")
    transaction_tab, question_tab = st.tabs(
        ["Ghi giao dịch bằng AI", "Hỏi đáp chi tiêu"]
    )

    with transaction_tab:
        st.subheader("Ghi giao dịch bằng AI")
        st.caption(
            "Nhập nhiều khoản bằng ngôn ngữ tự nhiên. Hãy kiểm tra và sửa kết quả "
            "trước khi lưu vào MySQL."
        )
        text = st.text_area(
            "Nội dung giao dịch",
            placeholder="Ví dụ: Sáng ăn phở 45k, trưa mua sách 120k, mẹ chuyển khoản 2 triệu",
            key="ai_transaction_input",
        )
        if st.button("Phân tích giao dịch", key="analyze_transactions"):
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
            st.markdown("#### Kiểm tra và chỉnh sửa")
            st.caption("Chỉ các khoản được xác nhận bên dưới mới được ghi vào cơ sở dữ liệu.")
            reviewed: list[dict] = []
            for index, row in enumerate(rows):
                with st.container(border=True):
                    st.markdown(f"**Giao dịch {index + 1}**")
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
                "Xác nhận và lưu giao dịch", type="primary", key="confirm_ai_transactions"
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
            st.dataframe(display, hide_index=True, use_container_width=True)

    with question_tab:
        st.subheader("Hỏi đáp chi tiêu")
        st.caption("Câu trả lời có thể sử dụng dữ liệu giao dịch của tài khoản đang đăng nhập.")
        columns = st.columns(len(QA_SUGGESTIONS))
        for index, (column, suggestion) in enumerate(zip(columns, QA_SUGGESTIONS)):
            if column.button(suggestion, key=f"ai_question_suggestion_{index}", use_container_width=True):
                st.session_state["ai_question_input"] = suggestion
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
                        st.session_state["ai_answer"] = request(
                            "finance.ask", {"question": question.strip()}
                        )
                    st.session_state["ai_last_question"] = question.strip()
                except Exception as error:
                    st.error(f"Không lấy được câu trả lời: {error}")
        if st.session_state.get("ai_answer"):
            st.markdown(f"**Bạn hỏi:** {st.session_state.get('ai_last_question', '')}")
            result = st.session_state["ai_answer"]
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
                        "Chi nhiều nhất",
                        summary.get("top_category") or "Chưa có dữ liệu",
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
                st.markdown(result.get("answer", ""))
            else:
                st.markdown(str(result))
