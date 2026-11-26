"""Shared presentation helpers for the Streamlit frontend."""

from contextlib import AbstractContextManager
from typing import Any

import streamlit as st


APP_STYLES = """
<style>
:root {
    --aea-blue: #2563eb;
    --aea-blue-dark: #1d4ed8;
    --aea-ink: #172b4d;
    --aea-muted: #64748b;
    --aea-border: #e2e8f0;
    --aea-canvas: #f5f8fc;
    --aea-surface: #ffffff;
}

.stApp {
    background: var(--aea-canvas);
    color: var(--aea-ink);
    color-scheme: light;
    font-family: Inter, "Segoe UI", sans-serif;
}

.block-container {
    max-width: 1440px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid var(--aea-border);
}

button[kind="primary"] {
    border-color: var(--aea-blue);
    background: var(--aea-blue);
    color: #ffffff;
}

button[kind="primary"]:hover {
    border-color: var(--aea-blue-dark);
    background: var(--aea-blue-dark);
    color: #ffffff;
}

.aea-brand {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin: 0.15rem 0 1.5rem;
}

.aea-brand-mark {
    display: grid;
    width: 2.5rem;
    height: 2.5rem;
    place-items: center;
    border-radius: 0.8rem;
    background: var(--aea-blue);
    color: #ffffff;
    font-size: 1.05rem;
    font-weight: 750;
}

.aea-brand-name {
    color: var(--aea-ink);
    font-size: 1rem;
    font-weight: 700;
    line-height: 1.25;
}

.aea-brand-caption {
    margin-top: 0.18rem;
    color: var(--aea-muted);
    font-size: 0.72rem;
    letter-spacing: 0.04em;
}

.aea-page-eyebrow {
    margin-bottom: 0.25rem;
    color: var(--aea-blue-dark);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
}

@media (max-width: 768px) {
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2rem;
    }
}
</style>
"""


def apply_design_system() -> None:
    """Apply the shared light fintech canvas and sidebar styling."""
    st.markdown(APP_STYLES, unsafe_allow_html=True)


def render_brand() -> None:
    """Render the compact application mark used in the sidebar."""
    st.markdown(
        """
        <div class="aea-brand">
            <div class="aea-brand-mark">A</div>
            <div>
                <div class="aea-brand-name">AI Expense Assistant</div>
                <div class="aea-brand-caption">PERSONAL FINANCE</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str | None = None) -> None:
    """Render a consistent page title and optional supporting text."""
    st.markdown(
        '<div class="aea-page-eyebrow">AI Expense Assistant</div>',
        unsafe_allow_html=True,
    )
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def section_container() -> Any:
    """Return a native bordered Streamlit container for a content section."""
    return st.container(border=True)


def render_metric_card(label: str, value: str, delta: str | None = None) -> None:
    """Render a metric in the shared bordered card treatment."""
    with section_container():
        st.metric(label, value, delta=delta)


def loading_state(label: str) -> AbstractContextManager:
    """Return Streamlit's native spinner context manager."""
    return st.spinner(label)


def render_empty_state(message: str) -> None:
    """Render a calm, consistent empty state using a native Streamlit notice."""
    st.info(message)


def render_error_state(message: str) -> None:
    """Render an error using Streamlit's accessible native error notice."""
    st.error(message)
