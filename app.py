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
    save_followup_log
)
from feedback_app.prompts import (
    TUTOR_SYSTEM_PROMPT,
    INITIAL_FEEDBACK_TEMPLATE,
    EVALUATION_PROMPT_TEMPLATE
)




# Path to your dataset
CSV_PATH = r'C:\repos\summer_project\filtered_augmented_posts\data\student_math_work_posts_augmented_successful_only.csv'
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
        st.session_state.student_attempt = row["question"]
        st.session_state.correct_solution = row.get("solution", "")
        st.session_state.similar_problem = row.get("new_problem", "")
        st.session_state.similar_solution = row.get("new_sol", "")

        print("Problem statement: ")

        st.session_state.messages = start_session(
            st.session_state.problem,
            st.session_state.student_attempt,
            st.session_state.correct_solution,
            TUTOR_SYSTEM_PROMPT,
            INITIAL_FEEDBACK_TEMPLATE
        )
        #need to come back to this i feel like i am missing smth!!

        st.session_state.mode = "initial_feedback"  # new mode before full tutoring
        st.session_state.student_reply = ""
        st.session_state.show_rubric = False
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
</style>
"""

st.markdown(chat_styles, unsafe_allow_html=True)
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

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
                st.session_state.mode = "main"

        else:  # normal tutoring session mode
            gpt_reply = continue_session(st.session_state.messages)
            st.session_state.messages.append({
                "role": "assistant",
                "content": gpt_reply
            })

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
    st.markdown(f"**New Problem**: {st.session_state.similar_problem}")

    one_shot = st.text_area("✍️ Your one-shot solution:")

    if st.button("📝 Submit Answer") and one_shot.strip() != "":
        st.session_state.feedback = evaluate_followup(
            st.session_state.similar_problem,
            one_shot,
            st.session_state.similar_solution,
            EVALUATION_PROMPT_TEMPLATE
        )
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

        st.markdown("Rate each from 1 (worst) to 5 (best):")

        st.radio("Revealed solution too early", [1, 2, 3, 4, 5], key="rubric_early", horizontal=True)
        st.radio("Misunderstood my ideas", [1, 2, 3, 4, 5], key="rubric_misunderstood", horizontal=True)
        st.radio("Gave constructive hints", [1, 2, 3, 4, 5], key="rubric_hints", horizontal=True)
        st.radio("Misled me", [1, 2, 3, 4, 5], key="rubric_mislead", horizontal=True)


        if st.button("Submit Evaluation"):
            rubric_scores = {
                "Revealed too early": st.session_state.rubric_early,
                "Misunderstood ideas": st.session_state.rubric_misunderstood,
                "Constructive hints": st.session_state.rubric_hints,
                "Misleading": st.session_state.rubric_mislead
            }

            def save_rubric_feedback(problem, rubric_scores):
                with open("rubric_feedback_log.json", "a") as f:
                    json.dump({
                        "problem": problem,
                        "rubrics": rubric_scores,
                        "timestamp": str(datetime.now())
                    }, f)
                    f.write("\n")

            save_rubric_feedback(st.session_state.similar_problem, rubric_scores)
            st.success("✅ Thanks for your feedback!")
            st.session_state.show_rubric = False
