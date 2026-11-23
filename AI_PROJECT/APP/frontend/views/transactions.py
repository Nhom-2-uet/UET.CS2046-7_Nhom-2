from datetime import date

import pandas as pd
import streamlit as st

from frontend.api_client import request


TYPE_LABELS = {"expense": "Chi tiêu", "income": "Thu nhập"}
TYPE_VALUES = {label: value for value, label in TYPE_LABELS.items()}


def _format_vnd(amount: int) -> str:
    return f"{amount:,.0f} đ".replace(",", ".")


def _record_dict(record) -> dict:
    return {
        "transaction_id": record.transaction_id,
        "transaction_date": record.transaction_date,
        "description": record.description or "",
        "category_name": record.category_name,
        "transaction_type": record.transaction_type,
        "amount_vnd": record.amount_vnd,
    }


def _load_categories(transaction_type: str) -> list[str]:
    return [
        row["name"]
        for row in request(
            "transaction.categories", {"transaction_type": transaction_type}
        )
    ]


def render_transactions() -> None:
    st.header("Quản lý giao dịch")
    st.caption("Giao dịch được tải và lưu trực tiếp qua backend.")

    add_col, refresh_col = st.columns([4, 1])
    with add_col:
        st.subheader("Thêm giao dịch")
    with refresh_col:
        if st.button("Làm mới", use_container_width=True):
            st.rerun()

    with st.expander("➕ Thêm giao dịch mới", expanded=False):
        transaction_type_label = st.selectbox(
            "Loại giao dịch", list(TYPE_VALUES), key="new_transaction_type"
        )
        transaction_type = TYPE_VALUES[transaction_type_label]
        try:
            categories = _load_categories(transaction_type)
        except Exception as error:
            st.error(f"Không tải được danh mục: {error}")
            categories = []
        if not categories:
            st.warning("Chưa có danh mục đang hoạt động cho loại giao dịch này.")

        with st.form("add_transaction_form"):
            name = st.text_input("Tên giao dịch", placeholder="Ví dụ: Ăn sáng")
            amount = st.number_input("Số tiền (VND)", min_value=0, step=1000)
            transaction_date = st.date_input("Ngày giao dịch", value=date.today())
            category = st.selectbox("Danh mục", categories, disabled=not categories)
            submitted = st.form_submit_button(
                "Thêm giao dịch", disabled=not categories, width="stretch"
            )
        if submitted:
            try:
                with st.spinner("Đang lưu giao dịch..."):
                    request(
                        "transaction.create",
                        {
                            "description": name,
                            "amount_vnd": int(amount),
                            "transaction_date": transaction_date,
                            "category_name": category,
                            "transaction_type": transaction_type,
                        },
                    )
                st.success("Đã thêm giao dịch.")
                st.rerun()
            except Exception as error:
                st.error(f"Không thể thêm giao dịch: {error}")

    try:
        with st.spinner("Đang tải giao dịch..."):
            records = request("transaction.list")
    except Exception as error:
        st.error(f"Không tải được danh sách giao dịch: {error}")
        return

    transactions = pd.DataFrame([_record_dict(row) for row in records])
    st.subheader("Lịch sử giao dịch")
    if transactions.empty:
        st.info("Chưa có giao dịch nào.")
        return

    col_search, col_type, col_category = st.columns(3)
    search = col_search.text_input("Tìm kiếm", placeholder="Tên giao dịch")
    type_label = col_type.selectbox("Loại giao dịch", ["Tất cả", *TYPE_VALUES])
    category_name = col_category.selectbox(
        "Danh mục", ["Tất cả", *sorted(transactions["category_name"].unique())]
    )

    filtered = transactions.copy()
    if search:
        filtered = filtered[filtered["description"].str.contains(search, case=False, na=False)]
    if type_label != "Tất cả":
        filtered = filtered[filtered["transaction_type"] == TYPE_VALUES[type_label]]
    if category_name != "Tất cả":
        filtered = filtered[filtered["category_name"] == category_name]

    display = filtered.copy()
    display["Ngày"] = display["transaction_date"].map(lambda value: value.strftime("%d/%m/%Y"))
    display["Loại"] = display["transaction_type"].map(TYPE_LABELS)
    display["Số tiền"] = display["amount_vnd"].map(_format_vnd)
    st.dataframe(
        display[["Ngày", "description", "category_name", "Loại", "Số tiền"]].rename(
            columns={"description": "Tên giao dịch", "category_name": "Danh mục"}
        ),
        hide_index=True,
        use_container_width=True,
    )
    st.caption(f"Tìm thấy {len(filtered)} giao dịch.")

    transaction_ids = filtered["transaction_id"].astype(int).tolist()
    if not transaction_ids:
        return
    selected_id = st.selectbox("Chọn giao dịch để sửa hoặc xóa", transaction_ids)
    selected = transactions.loc[transactions["transaction_id"] == selected_id].iloc[0]
    with st.expander("✏️ Chỉnh sửa giao dịch"):
        current_type = selected["transaction_type"]
        edit_type_label = st.selectbox(
            "Loại giao dịch", list(TYPE_VALUES),
            index=list(TYPE_VALUES.values()).index(current_type),
            key=f"edit_type_{selected_id}",
        )
        edit_type = TYPE_VALUES[edit_type_label]
        try:
            edit_categories = _load_categories(edit_type)
        except Exception as error:
            st.error(f"Không tải được danh mục: {error}")
            edit_categories = []
        if selected["category_name"] not in edit_categories:
            edit_categories.append(selected["category_name"])
        with st.form(f"edit_transaction_{selected_id}"):
            edit_name = st.text_input("Tên giao dịch", value=selected["description"])
            edit_amount = st.number_input(
                "Số tiền (VND)", min_value=0, value=int(selected["amount_vnd"]), step=1000
            )
            edit_date = st.date_input("Ngày giao dịch", value=selected["transaction_date"])
            edit_category = st.selectbox(
                "Danh mục", edit_categories, key=f"edit_category_{selected_id}"
            )
            save = st.form_submit_button("Lưu thay đổi")
        if save:
            try:
                with st.spinner("Đang cập nhật giao dịch..."):
                    updated = request(
                        "transaction.update",
                        {
                            "transaction_id": int(selected_id),
                            "description": edit_name,
                            "amount_vnd": int(edit_amount),
                            "transaction_date": edit_date,
                            "category_name": edit_category,
                            "transaction_type": edit_type,
                        },
                    )
                if updated is None:
                    st.error("Không tìm thấy giao dịch để cập nhật.")
                else:
                    st.success("Đã cập nhật giao dịch.")
                    st.rerun()
            except Exception as error:
                st.error(f"Không thể cập nhật giao dịch: {error}")

    with st.expander("🗑️ Xóa giao dịch"):
        st.warning("Thao tác này xóa giao dịch khỏi cơ sở dữ liệu.")
        if st.button("Xóa giao dịch", key=f"delete_transaction_{selected_id}"):
            try:
                with st.spinner("Đang xóa giao dịch..."):
                    deleted = request(
                        "transaction.delete", {"transaction_id": int(selected_id)}
                    )
                if deleted:
                    st.success("Đã xóa giao dịch.")
                    st.rerun()
                else:
                    st.error("Không tìm thấy giao dịch để xóa.")
            except Exception as error:
                st.error(f"Không thể xóa giao dịch: {error}")
