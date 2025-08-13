import streamlit as st

# Hide the sidebar navigation
st.set_page_config(page_title="Learn with Piccolo", layout="wide")
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

# Check if consent has been given
if not st.session_state.get("consent_given"):
    st.warning("⚠️ You must first complete the consent form before beginning the study.")

    # Redirect to the consent page
    if st.button("Go to Consent Form"):
        st.switch_page("pages/0_Consent.py")

else:
    # If consent has been given, check if demographics have been submitted
    if not st.session_state.get("demographics_submitted"):
        st.success("✅ Consent completed. Please provide your demographic information.")

        # Redirect to demographics page
        if st.button("Go to Demographic Information"):
            st.switch_page("pages/2_Demographics.py")

    else:
        # If demographics have been submitted, show the start tutoring button
        st.success("✅ Demographic information collected. You may begin the study.")

        # Redirect to tutoring page
        if st.button("Start Tutoring"):
            st.switch_page("pages/1_FeedbackApp.py")
