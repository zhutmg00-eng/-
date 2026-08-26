"""Small, shared HTTP client for the Streamlit views."""

import os

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
APP_API_KEY = os.getenv("APP_API_KEY", "")
API_HEADERS = {"X-API-Key": APP_API_KEY} if APP_API_KEY else {}


def api_post(path: str, payload: dict) -> requests.Response:
    """Call a backend endpoint with a bounded timeout."""
    return requests.post(
        f"{API_BASE_URL}{path}",
        json=payload,
        headers=API_HEADERS,
        timeout=30,
    )


def show_api_error(response: requests.Response) -> None:
    """Render the backend's most useful error detail."""
    try:
        detail = response.json().get("detail", response.text)
    except ValueError:
        detail = response.text
    st.error(f"请求未完成（{response.status_code}）：{detail}")
