import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import settings
from utils.logger import logger

st.title("Customer Support AI Chatbot")
if "history" not in st.session_state:
    st.session_state.history = []

query = st.text_input("Enter your question:")


def _build_session() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=settings.REQUEST_RETRY_TOTAL,
        status_forcelist=settings.REQUEST_RETRY_STATUS_FORCELIST,
        backoff_factor=settings.REQUEST_RETRY_BACKOFF_FACTOR,
        allowed_methods=("GET", "POST"),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _post_query(session: requests.Session, text: str) -> dict:
    url = f"{settings.API_BASE_URL}/query"
    try:
        resp = session.post(
            url,
            json={"query": text},
            timeout=settings.REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise ValueError("Invalid server response type")
        return data
    except requests.exceptions.Timeout:
        logger.warning("Request timed out for /query")
        raise
    except requests.exceptions.RequestException as re:
        logger.error("Request to %s failed: %s", url, re)
        raise
    except ValueError:
        logger.exception("Failed to parse JSON from /query response")
        raise


if st.button("Send"):
    if not query.strip():
        st.warning("Please enter a question before sending.")
    else:
        with st.spinner("Contacting assistant..."):
            session = _build_session()
            try:
                result = _post_query(session, query)
                summary = result.get("summary") or ""
                st.session_state.history.append((query, summary))
            except requests.exceptions.Timeout:
                st.error("The server took too long to respond. Please try again.")
            except requests.exceptions.RequestException as e:
                st.error(f"Network error: {e}")
            except Exception:
                st.error("Unexpected error while contacting the server.")

for q, a in st.session_state.history:
    st.write(f"**User:** {q}")
    st.write(f"**Bot:** {a}")
