from datetime import date, datetime
from uuid import uuid4

import pandas as pd
import streamlit as st


TYPE_LABELS = {"expense": "Chi tiêu", "income": "Thu nhập"}
TYPE_VALUES = {label: value for value, label in TYPE_LABELS.items()}


def _mock_record(
    transaction_date: date,
    description: str,
    category_name: str,
    transaction_type: str,
    amount_vnd: int,
) -> dict:
    """Create a UI mock record using Backend-aligned field names."""
    return {
        "transaction_id": pd.NA,
        "mock_id": str(uuid4()),
        "transaction_date": transaction_date,
        "description": description,
        "category_name": category_name,
        "transaction_type": transaction_type,
        "amount_vnd": amount_vnd,
    }


def _mock_transactions() -> pd.DataFrame:
    records = [
        _mock_record(date(2026, 11, 10), "Ăn trưa", "Ăn uống", "expense", 35000),
        _mock_record(date(2026, 11, 9), "Tiền làm thêm", "Thu nhập", "income", 1500000),
        _mock_record(date(2026, 11, 8), "Mua sách", "Học tập", "expense", 120000),
        _mock_record(date(2026, 11, 7), "Đi xe bus", "Đi lại", "expense", 7000),
        _mock_record(date(2026, 11, 6), "Xem phim", "Giải trí", "expense", 80000),
    ]
    transactions = pd.DataFrame(records)
    transactions["transaction_id"] = pd.array(
        transactions["transaction_id"], dtype="Int64"
    )
    return transactions


def _migrate_legacy_session_transactions(transactions: pd.DataFrame) -> pd.DataFrame:
    """Keep records from an already-open session after the UI schema changes."""
    records = [
        _mock_record(
            transaction_date=datetime.strptime(row["Ngày"], "%d/%m/%Y").date(),
            description=row["Tên giao dịch"],
            category_name=row["Danh mục"],
            transaction_type=TYPE_VALUES[row["Loại"]],
            amount_vnd=int(row["Số tiền"]),
        )
        for _, row in transactions.iterrows()
    ]
    if not records:
        return pd.DataFrame(
            {
                "transaction_id": pd.Series(dtype="Int64"),
                "mock_id": pd.Series(dtype="object"),
                "transaction_date": pd.Series(dtype="object"),
                "description": pd.Series(dtype="object"),
                "category_name": pd.Series(dtype="object"),
                "transaction_type": pd.Series(dtype="object"),
                "amount_vnd": pd.Series(dtype="int64"),
            }
        )
    migrated = pd.DataFrame(records)
    migrated["transaction_id"] = pd.array(
        migrated["transaction_id"], dtype="Int64"
    )
    return migrated


def _format_vnd(amount: int) -> str:
    return f"{amount:,.0f} đ".replace(",", ".")


def _format_transaction_option(row: pd.Series, include_amount: bool = False) -> str:
    label = f"{row['transaction_date'].strftime('%d/%m/%Y')} - {row['description']}"
    if include_amount:
        label += f" - {row['amount_vnd']:,} đ"
    return label


def _get_record(transactions: pd.DataFrame, mock_id: str) -> pd.Series:
    return transactions.loc[transactions["mock_id"] == mock_id].iloc[0]


def _display_transactions(transactions: pd.DataFrame) -> pd.DataFrame:
    """Build display-only labels without changing the underlying records."""
    return pd.DataFrame(
        {
            "Ngày": transactions["transaction_date"].map(
                lambda value: value.strftime("%d/%m/%Y")
            ),
            "Tên giao dịch": transactions["description"],
            "Danh mục": transactions["category_name"],
            "Loại": transactions["transaction_type"].map(TYPE_LABELS),
            "Số tiền": transactions["amount_vnd"].map(_format_vnd),
        }
    )


def render_transactions() -> None:
    """Render transaction management using session-local mock data."""
    st.header("Quản lý giao dịch")
    st.caption("Theo dõi và quản lý các khoản thu chi của bạn.")

    if "transactions" not in st.session_state:
        st.session_state.transactions = _mock_transactions()
    elif "mock_id" not in st.session_state.transactions.columns:
        st.session_state.transactions = _migrate_legacy_session_transactions(
            st.session_state.transactions
        )

    with st.expander("➕ Thêm giao dịch mới", expanded=False):
        transaction_type_label = st.selectbox(
            "Loại giao dịch",
            ["Chi tiêu", "Thu nhập"],
            key="new_transaction_type",
        )

        if transaction_type_label == "Chi tiêu":
            category_options = [
                "Ăn uống", "Đi lại", "Học tập", "Giải trí", "Mua sắm", "Khác"
            ]
        else:
            category_options = ["Lương", "Làm thêm", "Thưởng", "Thu nhập khác"]

        with st.form("add_transaction_form"):
            transaction_name = st.text_input(
                "Tên giao dịch",
                placeholder="Ví dụ: Ăn sáng, mua sách...",
            )
            transaction_amount = st.number_input(
                "Số tiền (VND)", min_value=0, step=1000
            )
            transaction_date = st.date_input(
                "Ngày giao dịch", value=date.today()
            )
            transaction_category = st.selectbox(
                "Danh mục",
                category_options,
                key="new_transaction_category",
            )
            submitted = st.form_submit_button(
                "Thêm giao dịch", width="stretch"
            )

            if submitted:
                if not transaction_name.strip():
                    st.error("Vui lòng nhập tên giao dịch.")
                elif transaction_amount <= 0:
                    st.error("Số tiền phải lớn hơn 0.")
                else:
                    new_record = _mock_record(
                        transaction_date=transaction_date,
                        description=transaction_name.strip(),
                        category_name=transaction_category,
                        transaction_type=TYPE_VALUES[transaction_type_label],
                        amount_vnd=int(transaction_amount),
                    )
                    st.session_state.transactions = pd.concat(
                        [
                            st.session_state.transactions,
                            pd.DataFrame([new_record]),
                        ],
                        ignore_index=True,
                    )
                    st.session_state.transactions["transaction_id"] = pd.array(
                        st.session_state.transactions["transaction_id"],
                        dtype="Int64",
                    )
                    st.success("Thêm giao dịch thành công!")

    transaction_data = st.session_state.transactions.copy()
    st.subheader("Lịch sử giao dịch")

    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        search_text = st.text_input(
            "Tìm kiếm giao dịch", placeholder="Nhập tên giao dịch..."
        )
    with filter_col2:
        selected_type_label = st.selectbox(
            "Loại giao dịch", ["Tất cả", "Thu nhập", "Chi tiêu"]
        )
    with filter_col3:
        categories = ["Tất cả"] + transaction_data["category_name"].unique().tolist()
        selected_category = st.selectbox("Danh mục", categories)

    filtered_data = transaction_data.copy()
    if search_text:
        filtered_data = filtered_data[
            filtered_data["description"].str.contains(
                search_text, case=False, na=False
            )
        ]
    if selected_type_label != "Tất cả":
        selected_type = TYPE_VALUES[selected_type_label]
        filtered_data = filtered_data[
            filtered_data["transaction_type"] == selected_type
        ]
    if selected_category != "Tất cả":
        filtered_data = filtered_data[
            filtered_data["category_name"] == selected_category
        ]

    st.dataframe(_display_transactions(filtered_data), width="stretch", hide_index=True)
    st.caption(f"Tìm thấy {len(filtered_data)} giao dịch.")

    with st.expander("🗑️ Xóa giao dịch"):
        if filtered_data.empty:
            st.info("Không có giao dịch để xóa.")
        else:
            selected_delete_id = st.selectbox(
                "Chọn giao dịch cần xóa",
                filtered_data["mock_id"].tolist(),
                format_func=lambda mock_id: _format_transaction_option(
                    _get_record(transaction_data, mock_id), include_amount=True
                ),
                key="delete_transaction_selector",
            )
            if st.button("Xóa giao dịch", type="primary"):
                st.session_state.transactions = (
                    st.session_state.transactions.loc[
                        st.session_state.transactions["mock_id"] != selected_delete_id
                    ].reset_index(drop=True)
                )
                st.success("Đã xóa giao dịch thành công!")
                st.rerun()

    with st.expander("✏️ Chỉnh sửa giao dịch"):
        if transaction_data.empty:
            st.info("Chưa có giao dịch để chỉnh sửa.")
        else:
            selected_edit_id = st.selectbox(
                "Chọn giao dịch cần chỉnh sửa",
                transaction_data["mock_id"].tolist(),
                format_func=lambda mock_id: _format_transaction_option(
                    _get_record(transaction_data, mock_id)
                ),
                key="edit_transaction_selector_v2",
            )
            current_transaction = _get_record(transaction_data, selected_edit_id)
            record_mask = (
                st.session_state.transactions["mock_id"] == selected_edit_id
            )

            st.write("**Chỉnh sửa thông tin giao dịch**")
            edit_name = st.text_input(
                "Tên giao dịch",
                value=current_transaction["description"],
                key=f"edit_name_{selected_edit_id}",
            )
            edit_amount = st.number_input(
                "Số tiền (VND)",
                min_value=0,
                value=int(current_transaction["amount_vnd"]),
                step=1000,
                key=f"edit_amount_{selected_edit_id}",
            )
            edit_date = st.date_input(
                "Ngày giao dịch",
                value=current_transaction["transaction_date"],
                key=f"edit_date_{selected_edit_id}",
            )
            current_type_label = TYPE_LABELS[current_transaction["transaction_type"]]
            edit_type_label = st.selectbox(
                "Loại giao dịch",
                ["Chi tiêu", "Thu nhập"],
                index=["Chi tiêu", "Thu nhập"].index(current_type_label),
                key=f"edit_type_{selected_edit_id}",
            )

            if edit_type_label == "Chi tiêu":
                edit_category_options = [
                    "Ăn uống", "Đi lại", "Học tập", "Giải trí", "Mua sắm", "Khác"
                ]
            else:
                edit_category_options = [
                    "Lương", "Làm thêm", "Thưởng", "Thu nhập khác"
                ]
            current_category = current_transaction["category_name"]
            if current_category not in edit_category_options:
                edit_category_options.append(current_category)
            edit_category = st.selectbox(
                "Danh mục",
                edit_category_options,
                index=edit_category_options.index(current_category),
                key=f"edit_category_{selected_edit_id}_{edit_type_label}",
            )

            if st.button("Lưu thay đổi", type="primary"):
                if not edit_name.strip():
                    st.error("Tên giao dịch không được để trống.")
                elif edit_amount <= 0:
                    st.error("Số tiền phải lớn hơn 0.")
                else:
                    st.session_state.transactions.loc[
                        record_mask, "description"
                    ] = edit_name.strip()
                    st.session_state.transactions.loc[
                        record_mask, "amount_vnd"
                    ] = int(edit_amount)
                    st.session_state.transactions.loc[
                        record_mask, "transaction_date"
                    ] = edit_date
                    st.session_state.transactions.loc[
                        record_mask, "transaction_type"
                    ] = TYPE_VALUES[edit_type_label]
                    st.session_state.transactions.loc[
                        record_mask, "category_name"
                    ] = edit_category
                    st.success("Cập nhật giao dịch thành công!")
                    st.rerun()
