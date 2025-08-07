import streamlit as st
import openai
import pandas as pd
from datetime import datetime
import json
from feedback_app.interactiveAgent import (
    start_session,
    continue_session,
    evaluate_followup,
    save_session_log,
    save_followup_log,
    save_session_to_google_sheet
)
from feedback_app.prompts import (
    TUTOR_SYSTEM_PROMPT,
    INITIAL_FEEDBACK_TEMPLATE,
    EVALUATION_PROMPT_TEMPLATE
)

from feedback_app.instructions import (
    DIALOGUE_INSTRUCTIONS,
    FOLLOWUP_INSTRUCTIONS,
    RUBRIC_INSTRUCTIONS
)


st.set_page_config(page_title="Tutoring", layout="wide")

# Hide sidebar nav
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

if not st.session_state.get("consent_given"):
    st.warning("Consent required. Redirecting...")
    st.switch_page("0. Consent")

# Path to your dataset
CSV_PATH = r'data/student_math_work_posts_augmented_successful_only.csv'
df = pd.read_csv(CSV_PATH)

# -------- Streamlit Config --------
st.set_page_config(page_title="Tutoring Agent", layout="wide")
st.markdown("""
    <style>
        html, body, [class*="css"]  {
            font-size: 25px !important;
        }
        textarea, input {
            font-size: 25px !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("💡 AI Tutoring System")

# -------- Sidebar --------
with st.sidebar:
    st.header("🔢 Select Problem Row")
    row_index = st.number_input("Row index (starting from 0)", min_value=0, max_value=len(df)-1, step=1) - 2

    if st.button("🔁 Load Row"):
        row = df.iloc[row_index]
        st.session_state.problem = row["problem_statement"]
        #st.session_state.student_attempt = row["question"]
        st.session_state.correct_solution = row.get("solution", "")
        st.session_state.similar_problem = row.get("new_problem", "")
        st.session_state.similar_solution = row.get("new_sol", "")

        st.session_state.mode = "awaiting_first_attempt"
        st.session_state.messages = []
        st.session_state.student_reply = ""
        st.rerun()


# -------- Guard Clause --------
if "messages" not in st.session_state:
    st.info("👈 Choose a row from the sidebar to begin.")
    st.stop()

# -------- Context --------
# st.subheader("📘 Tutoring Context")
# st.markdown(f"**Problem**: {st.session_state.problem}")
# st.markdown(f"**Student Attempt**: {st.session_state.student_attempt}")

# -------- Chat Display --------
st.subheader("Chat with Tutor")

st.markdown(f'<div class="instruction-box">{DIALOGUE_INSTRUCTIONS}</div>', unsafe_allow_html=True)

chat_styles = """
<style>
.chat-container {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-top: 10px;
    padding-left: 10px;
    padding-right: 10px;
}

.bubble {
    padding: 12px 16px;
    border-radius: 12px;
    border: 2px solid;
    background-color: #000000;
    font-family: sans-serif;
    font-size: 16px;
    display: inline-block;
    max-width: 70%;
    word-wrap: break-word;
    margin-top: 6px;
    margin-bottom: 6px;
}

.student {
    border-color: #ff4d4d;
    color: #ff4d4d;
    align-self: flex-end;
    text-align: left;
    font-size: 20px;
}

.tutor {
    border-color: #3399ff;
    color: #3399ff;
    align-self: flex-start;
    text-align: left;
    font-size: 20px;
}

.instruction-box {
    font-size: 30px;
    font-weight: 600;
    line-height: 1.6;
    margin-top: 20px;
    margin-bottom: 20px;
    color: #4CAF50; /* A pleasant green */
    background-color: rgba(76, 175, 80, 0.1); /* Subtle green tint */
    padding: 12px;
    border-left: 5px solid #4CAF50;
    border-radius: 6px;
}

</style>
"""

st.markdown(chat_styles, unsafe_allow_html=True)
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

if st.session_state.get("mode") == "awaiting_first_attempt":
    st.subheader("✍️ Submit Your First Attempt")
    st.markdown(f"**Problem:** {st.session_state.problem}")

    first_attempt = st.text_area("Your one-shot solution:", key="first_attempt")
    st.session_state["attempt_submitted"] = True 
    
    if st.button("🚀 Submit Initial Attempt") and first_attempt.strip():
        st.session_state.student_attempt = first_attempt.strip()

        st.session_state.session_log_data = {
            "problem": st.session_state.problem,
            "student_attempt": st.session_state.student_attempt,
            "correct_solution": st.session_state.correct_solution,
            "messages": [],
            "similar_problem": st.session_state.similar_problem,
            "similar_solution": st.session_state.similar_solution,
            "followup_response": "",
            "followup_feedback": "",
            "rubrics": {},
            "timestamp": str(datetime.now())
        }

        # Now start the session using the user's typed answer
        st.session_state.messages = start_session(
            st.session_state.problem,
            st.session_state.student_attempt,
            st.session_state.correct_solution,
            TUTOR_SYSTEM_PROMPT,
            INITIAL_FEEDBACK_TEMPLATE
        )

        st.session_state.session_log_data["messages"] = st.session_state.messages

        st.session_state.mode = "initial_feedback"
        st.rerun()

for msg in st.session_state.messages[1:]:
    role = msg["role"]
    content = msg["content"].replace("\n", "<br>")

    if role == "user":
        bubble = f'<div class="bubble student">🧑‍🎓 <b>Student:</b><br>{content}</div>'
    elif role == "assistant":
        bubble = f'<div class="bubble tutor">🤖 <b>Tutor:</b><br>{content}</div>'
    
    st.markdown(bubble, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# -------- Input Interaction --------
def send_and_clear():
    if st.session_state.student_reply.strip() != "":
        user_msg = st.session_state.student_reply.strip()
        st.session_state.messages.append({
            "role": "user",
            "content": user_msg
        })

        st.session_state.session_log_data["messages"] = st.session_state.messages

        if st.session_state.mode == "initial_feedback":
            # GPT replies as tutor clarifying initial feedback
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=st.session_state.messages
            )
            gpt_reply = response.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": gpt_reply})

            # If user types "start" or "continue", switch mode to main tutoring session
            if user_msg.lower() in ["start", "continue"]:
                st.session_state.messages = start_session(
                    st.session_state.problem,
                    st.session_state.student_attempt,
                    st.session_state.correct_solution,
                    TUTOR_SYSTEM_PROMPT
                )
                st.session_state.session_log_data["messages"] = st.session_state.messages
                st.session_state.mode = "main"
                

        else:  # normal tutoring session mode
            gpt_reply = continue_session(st.session_state.messages)
            st.session_state.messages.append({
                "role": "assistant",
                "content": gpt_reply
            })
            st.session_state.session_log_data["messages"] = st.session_state.messages


        st.session_state.student_reply = ""
        st.rerun()

# -------- Show input during initial and main mode --------
if st.session_state.get("mode") in ["initial_feedback", "main"]:
    st.text_input(
        "✍️ Enter your reply or question to the tutor:",
        key="student_reply"
    )
    st.button("📨 Send Reply", on_click=send_and_clear)


# -------- Finish Phase --------
if st.session_state.get("attempt_submitted"):
    if st.button("✅ Finish Tutoring / Go to Follow-up"):
        st.session_state.mode = "followup"
        save_session_log(
            st.session_state.problem,
            st.session_state.student_attempt,
            st.session_state.correct_solution,
            st.session_state.messages
        )
        st.rerun()

# -------- Follow-Up --------
if st.session_state.get("mode") == "followup":
    st.subheader("🧪 Try a Similar Problem")
    st.markdown(f'<div class="instruction-box">{FOLLOWUP_INSTRUCTIONS}</div>', unsafe_allow_html=True)
    st.markdown(f"**New Problem**: {st.session_state.similar_problem}")

    one_shot = st.text_area("✍️ Your one-shot solution:")

    if st.button("📝 Submit Answer") and one_shot.strip() != "":
        feedback = evaluate_followup(
            st.session_state.similar_problem,
            one_shot,
            st.session_state.similar_solution,
            EVALUATION_PROMPT_TEMPLATE
        )
        st.session_state.feedback = feedback
        st.session_state.session_log_data["followup_response"] = one_shot
        st.session_state.session_log_data["followup_feedback"] = feedback
        st.session_state.session_log_data["timestamp"] = str(datetime.now())
        
        save_followup_log(
            st.session_state.similar_problem,
            one_shot,
            st.session_state.similar_solution,
            st.session_state.feedback
        )
        st.session_state.show_feedback = True  # trigger display of feedback

    # Display feedback (if already submitted)
    if st.session_state.get("show_feedback"):
        st.markdown("### 🎯 Tutor Feedback:")
        st.success(st.session_state.feedback)

        if st.button("🧠 Rate your experience"):
            st.session_state.show_rubric = True


    # Rubric evaluation
    if st.session_state.get("show_rubric"):
        st.markdown("## 🧪 Evaluate the Tutoring Experience")
        st.markdown(f'<div class="instruction-box">{RUBRIC_INSTRUCTIONS}</div>', unsafe_allow_html=True)

        st.markdown("Rate each from 1 (worst) to 5 (best):")

        st.radio("Diagnostic - the tutor correctly pointed out where and what the errors were in my judgement whenever i shared my own thoughts", [1, 2, 3, 4, 5], key="rubric_diagnostic", horizontal=True)
        st.radio("Correctness - the tutor does not make incorrect statements and is relevant to the current question and my answer", [1, 2, 3, 4, 5], key="rubric_correctness", horizontal=True)
        st.radio("Not Revealing - the tutor did not directly reveal the correct answer to me", [1, 2, 3, 4, 5], key="rubric_not_rev", horizontal=True)
        st.radio("Applicable - the tutor gave me sound suggestions/hints that, when followed, have guided me to the correct solution", [1, 2, 3, 4, 5], key="rubric_applicable", horizontal=True)
        st.radio("Positive - the feedback is positive and has an encouraging tone", [1, 2, 3, 4, 5], key="rubric_positive", horizontal=True)

        if st.button("Submit Evaluation"):
            rubric_scores = {
                "Diagnostic": st.session_state.rubric_diagnostic,
                "Correctness": st.session_state.rubric_correctness,
                "Not Revealing": st.session_state.rubric_not_rev,
                "Applicable": st.session_state.rubric_applicable,
                "Positive": st.session_state.rubric_positive,
            }

            st.session_state.session_log_data["rubrics"] = rubric_scores

            def save_rubric_feedback(problem, rubric_scores):
                with open("rubric_feedback_log.json", "a") as f:
                    json.dump({
                        "problem": problem,
                        "rubrics": rubric_scores,
                        "timestamp": str(datetime.now())
                    }, f)
                    f.write("\n")

            save_rubric_feedback(st.session_state.similar_problem, rubric_scores)
            save_session_to_google_sheet(st.session_state.session_log_data)

            st.success("✅ Thanks for your feedback!")
            st.session_state.show_rubric = False

