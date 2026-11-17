import pandas as pd
import plotly.express as px
import streamlit as st


def render_dashboard_charts() -> None:
    """Render the dashboard's current weekly and category mock charts."""
    weekly_data = pd.DataFrame(
        {
            "Tuần": ["Tuần 1", "Tuần 2", "Tuần 3", "Tuần 4"],
            "Thu nhập": [1_200_000, 1_300_000, 1_200_000, 1_300_000],
            "Chi tiêu": [500_000, 700_000, 600_000, 700_000],
        }
    )
    category_data = pd.DataFrame(
        {
            "Danh mục": ["Ăn uống", "Đi lại", "Học tập", "Giải trí", "Khác"],
            "Số tiền": [1_000_000, 400_000, 600_000, 300_000, 200_000],
        }
    )

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.subheader("Thu nhập và chi tiêu theo tuần")
        fig_bar = px.bar(
            weekly_data,
            x="Tuần",
            y=["Thu nhập", "Chi tiêu"],
            barmode="group",
            title="So sánh thu nhập và chi tiêu",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with chart_col2:
        st.subheader("Cơ cấu chi tiêu")
        fig_pie = px.pie(
            category_data,
            names="Danh mục",
            values="Số tiền",
            title="Chi tiêu theo danh mục",
        )
        st.plotly_chart(fig_pie, width="stretch")
