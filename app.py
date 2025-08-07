import streamlit as st

# Hide the sidebar navigation
st.set_page_config(page_title="AI Tutoring", layout="wide")
hide_sidebar = """
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
"""
st.markdown(hide_sidebar, unsafe_allow_html=True)

# Redirect to consent or main app
if not st.session_state.get("consent_given"):
    st.switch_page("pages/0_Consent.py")
else:
    st.switch_page("pages/1_FeedbackApp.py")
