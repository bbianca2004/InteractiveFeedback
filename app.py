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

# Landing logic
st.title("Welcome to the AI Tutoring Study")

if not st.session_state.get("consent_given"):
    st.warning("⚠️ You must first complete the consent form before beginning the study.")

    if st.button("Go to Consent Form"):
        st.switch_page("0_Consent")

else:
    st.success("✅ Consent completed. You may begin the study.")

    if st.button("Start Tutoring"):
        st.switch_page("1_FeedbackApp")
