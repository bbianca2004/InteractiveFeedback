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

st.title("📘 Study Instructions")

st.markdown("""
### What this is about  
You’ll be trying out an **AI tutoring system** designed to support student learning in *discrete mathematics (counting)*.  
The goal is to see whether interactive feedback can help students think more deeply and reflect on their reasoning.  

---

### What you’ll do  
1. Work through **three problems** – one easy, one medium, one hard.  
2. For each, write your own **detailed solution** (the tutor won’t accept just a number).  
3. The AI tutor will give **initial feedback**, and you can then have a short **back-and-forth conversation** to improve your solution.  
4. After both stages, you’ll rate the tutor’s response on a few simple rubrics.  
5. Finally, you’ll get a **follow-up problem** to test whether the feedback helped.  

---

### What to keep in mind  
- The problems are **intro-level (CS-101)** – easy on purpose, since the focus is interaction, not difficulty.  
- Please note anything that feels **confusing, buggy, or unhelpful**. Your impressions are just as valuable as your answers.  
- At the end, you can leave **general feedback**, or email me directly at [bianca.pitu@epfl.ch](mailto:bianca.pitu@epfl.ch).  

---

### One small ask  
Even if the process feels long or you lose motivation, please try to **complete all three problems**.  
Even quick, low-effort answers are better than stopping halfway.  

---

### Extra  
If you’d like, you can **repeat the study** and experiment with the tutor. Every run gives us more insights!  

---

### 💚 Thank you  
Thank you so much for your interest in this study, your time and feedback mean a lot!  
""")

# ✅ Confirmation button instead of radio
if st.button("✅ I confirm I have read the instructions"):
    st.session_state["instructions_read"] = True
    st.success("Thank you! Redirecting to the study...")
    st.switch_page("pages/1_FeedbackApp.py")
