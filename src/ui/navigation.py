"""Navigation callbacks shared by Streamlit views."""

import streamlit as st


def navigate_to(page: str) -> None:
    """Select a sidebar page before Streamlit reruns the application."""
    st.session_state["current_page"] = page
