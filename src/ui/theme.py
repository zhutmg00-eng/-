"""Visual language and small presentation helpers for the Streamlit app."""

from html import escape

import streamlit as st


CSS = """
<style>
:root {
    --ink: #17231d;
    --ink-soft: #506159;
    --canvas: #f4f7f5;
    --surface: #ffffff;
    --surface-muted: #e9efec;
    --line: #d7e0db;
    --brand: #1f6a4a;
    --brand-strong: #155239;
    --brand-soft: #dcece4;
    --amber: #a66212;
    --amber-soft: #fff1d8;
    --focus: #d18a2d;
}
html { scroll-behavior: smooth; }
body, [class*="css"] {
    color: var(--ink);
    font-family: "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
}
[data-testid="stAppViewContainer"] { background: var(--canvas); }
[data-testid="stMainBlockContainer"] {
    max-width: 1280px;
    padding-top: 4.5rem;
    padding-bottom: 4rem;
}
[data-testid="stHeader"] { background: rgba(244, 247, 245, 0.94); }
.app-brand {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 3.25rem;
    margin-bottom: 1.75rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--line);
}
.app-brand__identity { display: flex; align-items: center; gap: 0.75rem; }
.app-brand__mark, .sidebar-brand__mark {
    display: inline-grid;
    place-items: center;
    width: 2.25rem;
    height: 2.25rem;
    border-radius: 6px;
    background: var(--brand);
    color: white;
    font: 700 1rem/1 "Segoe UI", sans-serif;
}
.app-brand__name { color: var(--ink) !important; font-weight: 700; line-height: 1.1; }
.app-brand__meta, .app-brand__scope { color: var(--ink-soft) !important; }
.app-brand__meta { font-size: 0.78rem; }
.app-brand__scope { font-size: 0.8rem; font-variant-numeric: tabular-nums; }
.page-heading { max-width: 52rem; margin: 0 0 1.75rem; }
.page-heading__eyebrow {
    margin: 0 0 0.4rem;
    color: var(--brand-strong);
    font-size: 0.75rem;
    font-weight: 700;
}
.page-heading h1 {
    margin: 0;
    color: var(--ink);
    font-size: clamp(1.8rem, 3vw, 2.65rem);
    line-height: 1.12;
    letter-spacing: 0;
    text-wrap: balance;
}
.page-heading p:last-child {
    max-width: 66ch;
    margin: 0.65rem 0 0;
    color: var(--ink-soft);
    font-size: 0.98rem;
    line-height: 1.65;
    text-wrap: pretty;
}
.empty-state, .notice-panel {
    margin: 0.5rem 0 1rem;
    padding: 1rem 1.125rem 1.15rem;
    border-left: 3px solid var(--brand);
    background: var(--surface);
}
.empty-state strong, .notice-panel strong { display: block; margin-bottom: 0.3rem; }
.empty-state span, .notice-panel span {
    display: block;
    max-width: 68ch;
    color: var(--ink-soft);
    line-height: 1.55;
}
.notice-panel--amber { border-left-color: var(--amber); background: var(--amber-soft); }
.workflow-strip {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin: 0.75rem 0 1.5rem;
    border: 1px solid var(--line);
    border-radius: 8px;
    overflow: hidden;
    background: var(--surface);
}
.workflow-step { min-height: 7.25rem; padding: 1rem; border-right: 1px solid var(--line); }
.workflow-step:last-child { border-right: 0; }
.workflow-step__number {
    display: block;
    margin-bottom: 1rem;
    color: var(--brand);
    font-size: 0.75rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
}
.workflow-step strong { display: block; margin-bottom: 0.25rem; }
.workflow-step span { color: var(--ink-soft); font-size: 0.85rem; line-height: 1.45; }
.status-list { margin: 0; padding: 0; list-style: none; border-top: 1px solid var(--line); }
.status-list li {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    min-height: 3.25rem;
    border-bottom: 1px solid var(--line);
}
.status-list span { color: var(--ink-soft); }
.status-list strong { font-variant-numeric: tabular-nums; }
[data-testid="stSidebar"] { background: #17241e; }
[data-testid="stSidebar"] * { color: #f4f7f5; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #c7d3cc; }
[data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }
.sidebar-brand { display: flex; align-items: center; gap: 0.75rem; margin: 0 0 1.5rem; }
.sidebar-brand strong, .sidebar-brand small { display: block; }
.sidebar-brand strong { font-size: 1rem; }
.sidebar-brand small { margin-top: 0.15rem; color: #aebdb5; font-size: 0.72rem; }
.sidebar-brand__mark { background: #e3a64b; color: #17241e; }
.sidebar-note {
    margin-top: 2rem;
    padding: 0.9rem;
    border: 1px solid #425149;
    border-radius: 6px;
    background: #1d2d25;
}
.sidebar-note strong, .sidebar-note span { display: block; }
.sidebar-note strong { margin-bottom: 0.4rem; font-size: 0.76rem; }
.sidebar-note span { color: #b7c5bd; font-size: 0.72rem; line-height: 1.55; }
[data-testid="stSidebar"] [role="radiogroup"] { gap: 0.3rem; }
[data-testid="stSidebar"] [role="radiogroup"] label {
    min-height: 2.75rem;
    padding: 0.45rem 0.55rem;
    border-radius: 6px;
    transition: background-color 160ms ease;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background: #263a30; }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) { background: #314a3d; }
h2, h3 { color: var(--ink); letter-spacing: 0; text-wrap: balance; }
h2 { margin-top: 1.5rem !important; font-size: 1.3rem !important; }
h3 { font-size: 1.05rem !important; }
p, label, [data-testid="stCaptionContainer"] { line-height: 1.55; }
a { text-decoration-thickness: 1px; text-underline-offset: 3px; }
[data-testid="stMetric"] {
    min-height: 7rem;
    padding: 0.9rem 1rem;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--surface);
}
[data-testid="stMetricLabel"] { color: var(--ink-soft); }
[data-testid="stMetricValue"] {
    color: var(--ink);
    font-size: clamp(1.25rem, 2vw, 1.7rem);
    font-variant-numeric: tabular-nums;
}
.stButton > button, .stDownloadButton > button {
    min-height: 2.75rem;
    border-radius: 6px;
    font-weight: 600;
    transition: border-color 160ms ease, background-color 160ms ease, transform 100ms ease;
}
.stButton > button:active, .stDownloadButton > button:active { transform: translateY(1px); }
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
    border-color: var(--brand);
    background: var(--brand);
}
.stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {
    border-color: var(--brand-strong);
    background: var(--brand-strong);
}
button:focus-visible, input:focus-visible, textarea:focus-visible,
[role="radio"]:focus-visible, [role="slider"]:focus-visible, a:focus-visible {
    outline: 3px solid var(--focus) !important;
    outline-offset: 2px !important;
}
[data-baseweb="input"] > div, [data-baseweb="select"] > div,
[data-baseweb="textarea"] > div { border-radius: 6px; background: var(--surface); }
[data-testid="stForm"] {
    padding: 1rem;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--surface);
}
[data-testid="stDataFrame"], [data-testid="stTable"] { border: 1px solid var(--line); border-radius: 6px; }
[data-testid="stExpander"] { border-color: var(--line); border-radius: 6px; background: var(--surface); }
[data-testid="stAlert"] { border-radius: 6px; }
[data-testid="stChatMessage"] {
    padding: 1rem;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--surface);
}
hr { border-color: var(--line) !important; }
@media (max-width: 768px) {
    [data-testid="stMainBlockContainer"] { padding: 4rem 1rem 3rem; }
    .app-brand { align-items: flex-start; gap: 0.75rem; }
    .app-brand__scope { max-width: 10rem; text-align: right; }
    .workflow-strip { grid-template-columns: 1fr; }
    .workflow-step { min-height: auto; border-right: 0; border-bottom: 1px solid var(--line); }
    .workflow-step:last-child { border-bottom: 0; }
    div[data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        flex: 1 1 min(100%, 18rem) !important;
        width: 100% !important;
    }
    .stButton > button, .stDownloadButton > button { width: 100%; min-height: 2.75rem; }
}
@media (max-width: 360px) {
    .app-brand__scope { display: none; }
    .page-heading h1 { font-size: 1.7rem; }
    [data-testid="stMetric"] { min-height: 6rem; }
}
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        scroll-behavior: auto !important;
        transition-duration: 0.01ms !important;
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
    }
}
</style>
"""


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def render_brand() -> None:
    st.markdown(
        """
        <div class="app-brand">
            <div class="app-brand__identity">
                <span class="app-brand__mark" aria-hidden="true">C</span>
                <span><span class="app-brand__name">碳路</span><br>
                <span class="app-brand__meta">物流碳决策工作台</span></span>
            </div>
            <span class="app-brand__scope">直接运营排放 · 科研原型</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_header(eyebrow: str, title: str, description: str) -> None:
    st.markdown(
        f"""
        <header class="page-heading">
            <p class="page-heading__eyebrow">{escape(eyebrow)}</p>
            <h1>{escape(title)}</h1>
            <p>{escape(description)}</p>
        </header>
        """,
        unsafe_allow_html=True,
    )


def empty_state(title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="empty-state" role="status">
            <strong>{escape(title)}</strong>
            <span>{escape(description)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def notice(title: str, description: str, *, amber: bool = False) -> None:
    modifier = " notice-panel--amber" if amber else ""
    st.markdown(
        f"""
        <div class="notice-panel{modifier}" role="note">
            <strong>{escape(title)}</strong>
            <span>{escape(description)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
