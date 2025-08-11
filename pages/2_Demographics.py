# demographics.py (Streamlit page for collecting demographic data)

import streamlit as st

st.set_page_config(page_title="Demographic Information", layout="wide")

# Check if consent is given
if "consent_given" not in st.session_state or not st.session_state["consent_given"]:
    st.warning("⚠️ You must consent before filling out demographic information.")
    st.stop()

# Demographic form
st.title("👤 Demographic Information")

st.markdown("Please provide some demographic details. This information will be anonymized and used for research purposes only.")

age = st.slider("Age", 18, 100, 18)
gender = st.selectbox("Gender", ["Select", "Male", "Female", "Non-binary", "Other"])
academic_level = st.selectbox("Highest study level(achieved or ongoing):", ["Select", "Highschool", "Bachelor", "Masters", "PhD"])
academic_background = st.text_input("Academic Background (e.g., Degree, Major)")

# You can add more demographic fields as needed
other_details = st.text_area("Any additional details you'd like to share (optional)")

if age and gender != "Select" and academic_level != "Select" and academic_background:
    submit_button = st.button("Submit Demographics")
else:
    submit_button = None
    st.warning("⚠️ Please fill out all required fields before submitting.")

if submit_button:
    st.session_state.demographics = {
        "age": age,
        "gender": gender,
        "academic_background": academic_background,
        "academic_level": academic_level
    }
    st.success("Demographic information saved!")
    st.session_state["demographics_submitted"] = True

    # After demographic info is saved, you can move to the tutoring page
    st.switch_page("pages/1_FeedbackApp.py")
