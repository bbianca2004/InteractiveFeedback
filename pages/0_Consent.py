import streamlit as st

st.set_page_config(page_title="Consent", layout="wide")

# Hide sidebar nav
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📘 Study Consent Form")

st.markdown("""
    ### Welcome to the Tutoring Study

    Thank you for participating in our research on AI-based tutoring in mathematics. Please read the following information carefully before proceeding.

    ---  

    ### About the Study

    This study is conducted by researchers at the **ML4ED Lab at EPFL**. Our goal is to evaluate how students interact with AI tutors and how helpful these systems are in supporting learning.

    You will:
    - Attempt to solve three discrete mathematics problem.
    - Receive feedback from an AI tutor.
    - Engage in a conversation to improve your solution.
    - Try a follow-up problem.
    - Rate your experience.

    The entire study takes around **25-30 minutes**.

    ---

    ### Ethical Approval and Data Use

    This study has been approved by the **EPFL Human Research Ethics Committee**.

    By participating, you acknowledge and agree to the following:

    - Your responses and interactions will be **anonymized** and used **strictly for research purposes**.
    - No personal identifiers will be collected.
    - You may **withdraw at any time**, and your data will be deleted.
    - Data will be securely stored and may be used in academic publications in aggregate form.
    - You can request access to your data at any time by contacting the research team.

    If you have any questions, feel free to contact the study organizer: **bianca.pitu@epfl.ch**

    ---

    ### Consent

    By proceeding, you confirm that:
    - You understand the purpose and structure of the study.
    - You agree for your data to be used for research and publication.
    - You are at least 18 years old and a university-level student.

    """)

consent = st.radio("Do you consent to participate?", ["Yes", "No"], index=None)

if consent == "Yes":
    st.session_state["consent_given"] = True
    st.success("✅ Consent recorded. Redirecting...")
    st.switch_page("pages/1_FeedbackApp.py")
elif consent == "No":
    st.warning("You must consent to proceed.")
    st.stop()
