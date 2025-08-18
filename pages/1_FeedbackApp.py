import streamlit as st
import openai
import pandas as pd
from datetime import datetime
import json
import math
import re
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


#st.set_page_config(page_title="Tutoring", layout="wide")
st.set_page_config(page_title="Tutoring Agent", layout="wide")



# --------- Initialisation of session-wide log data ----------
if "student_id" not in st.session_state:
    st.session_state.student_id = f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

if "demographics" not in st.session_state:
    st.session_state.demographics = {
        "age": "",
        "gender": "",
        "academic_background": "",
        "academic_level": ""
    }

if "session_log_data" not in st.session_state:
    st.session_state.session_log_data = {
        "student_id": st.session_state.student_id,
        "demographics": st.session_state.demographics,
        "tasks": []
    }
    st.session_state.task_completed = False

if "show_initial_rubric" not in st.session_state:
    st.session_state.show_initial_rubric = False

if "finish_button_clicked" not in st.session_state:
    st.session_state.finish_button_clicked = False

if "initial_rubric_submitted" not in st.session_state:
    st.session_state.initial_rubric_submitted = False

if "task_index" not in st.session_state:
    st.session_state.task_index = 0

if "task_log" not in st.session_state:
    st.session_state.task_log = {}

if "api_messages" not in st.session_state:
    st.session_state.api_messages = []     # includes system, what you send to OpenAI

if "transcript" not in st.session_state:
    st.session_state.transcript = [] 


# ---------- SIDEBAR PROGRESS INDICATOR ----------
def render_sidebar_stepper(current_step, steps):
    sidebar_html = '<div style="padding: 20px 10px;">'
    for i, label in enumerate(steps):
        if i < current_step:
            color = "#4CAF50"  # green - completed
            emoji = "✅"
        elif i == current_step:
            color = "#2196F3"  # blue - current
            emoji = "🔵"
        else:
            color = "#ccc"     # gray - upcoming
            emoji = "⚪"

        sidebar_html += (
            f'<div style="margin-bottom: 15px;">'
            f'<div style="font-weight: bold; color: {color};">'
            f'{emoji} Task {i+1}: {label}'
            f'</div></div>'
        )
    sidebar_html += "</div>"
    st.sidebar.markdown(sidebar_html, unsafe_allow_html=True)

# Call the stepper
render_sidebar_stepper(
    st.session_state.task_index,
    ["Easy", "Medium", "Hard"]
)

# Visual progress bar
progress = (st.session_state.task_index + 1) / 3
st.sidebar.progress(progress, text=f"{st.session_state.task_index + 1} of 3 tasks completed")

if not st.session_state.get("consent_given"):
    st.warning("Consent required. Redirecting...")
    st.switch_page("pages/0_Consent.py")

# Path to your dataset
CSV_PATH = r'data/student_math_work_posts_augmented_successful_only.csv'
df = pd.read_csv(CSV_PATH)

# -------- Streamlit Config --------

# Set up task progression (Easy → Medium → Hard)
TASKS = [
    {"label": "Problem 1: Easy", "index": 5},
    {"label": "Problem 2: Medium", "index": 35},
    {"label": "Problem 3: Hard", "index": 3},
]

# Start at task 0 if not already started
if "task_index" not in st.session_state:
    st.session_state.task_index = 0

st.markdown("""
    <style>
        html, body, [class*="css"]  {
            font-size: 16px !important;
        }
        textarea, input {
            font-size: 16px !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- Toggle in sidebar ---
st.sidebar.subheader("🧮 Calculator")

# --- init session state ---
if "calc_expr" not in st.session_state:
    st.session_state.calc_expr = ""

# --- helper to update expression BEFORE the input is rendered ---
def _append(txt):
    if st.session_state.calc_expr == "Error":
        st.session_state.calc_expr = ""
    st.session_state.calc_expr += txt

def _evaluate():
    try:
        expr_eval = re.sub(r"\s+", "", st.session_state.calc_expr)

        # 5nCr3 or nCr(5,3)
        expr_eval = re.sub(r"(\d+)nCr(\d+)", r"math.comb(\1,\2)", expr_eval)
        expr_eval = expr_eval.replace("nCr(", "math.comb(")

        # 5nPr2 or nPr(5,2)
        expr_eval = re.sub(r"(\d+)nPr(\d+)", r"math.perm(\1,\2)", expr_eval)
        expr_eval = expr_eval.replace("nPr(", "math.perm(")

        # factorial like 5!
        while re.search(r"(\d+)!", expr_eval):
            expr_eval = re.sub(r"(\d+)!", r"math.factorial(\1)", expr_eval)

        result = eval(expr_eval, {"math": math, "__builtins__": None}, {})
        st.session_state.calc_expr = str(result)
    except Exception:
        st.session_state.calc_expr = "Error"

def _clear():
    st.session_state.calc_expr = ""

# --- buttons (we update state before rendering the input) ---
ops_map = {"÷": "/", "×": "*", "−": "-", "＋": "+"}

rows = [
    ["0","1","2","÷"],
    ["3","4","5","×"],
    ["6","7","8","−"],
    ["9",".","＋","="],
    ["nCr","nPr","n!","Clear"],
]

for r_idx, row in enumerate(rows):
    cols = st.sidebar.columns(4, gap="small")
    for c_idx, b in enumerate(row):
        # safe, alphanumeric key
        if cols[c_idx].button(b, key=f"btn_{r_idx}_{c_idx}"):
            if b == "=":
                _evaluate()
            elif b == "Clear":
                _clear()
            elif b == "n!":
                _append("!")
            elif b in ops_map:
                _append(ops_map[b])    # append real operator
            else:
                _append(b)

# --- NOW RENDER THE INPUT (binds to the updated state) ---
st.sidebar.text_input("Expression", key="calc_expr", placeholder="e.g. 5nCr3 + 2*4 or 5!")

st.sidebar.caption("Supports: `nCr`, `nPr`, factorial `!`, and basic arithmetic.")


st.title("💡 AI Tutoring System")

# -------- Task Progression --------
if st.session_state.task_index < len(TASKS):
    current_task = TASKS[st.session_state.task_index]
    selected_index = current_task["index"]
    row = df.iloc[selected_index - 2]

    # Only load if not already loaded
    if "problem" not in st.session_state or st.session_state.mode == "done":
        st.session_state.problem = row["problem_statement"]
        st.session_state.correct_solution = row.get("problem_solution", "")
        st.session_state.similar_problem = row.get("new_problem", "")
        st.session_state.similar_solution = row.get("new_solution", "")
        st.session_state.task_log = {}
        st.session_state.mode = "awaiting_first_attempt"

        st.session_state.api_messages = []               # what you send to the API
        st.session_state.transcript = []                 # what you render/save (no system)
        st.session_state.initial_feedback = ""        

        st.session_state.messages = []
        st.session_state.student_reply = ""
        st.session_state.attempt_submitted = False
        st.session_state.show_feedback = False
        st.session_state.show_rubric = False


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

.problem {
    border-color: #9b59b6;
    color: #9b59b6;
    align-self: center;
    text-align: left;
    font-size: 20px;
}

</style>
"""

st.markdown(chat_styles, unsafe_allow_html=True)
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

if st.session_state.get("mode") in ["initial_feedback", "main"] and "initial_feedback" in st.session_state:
    # problem bubble
    st.markdown(f'<div class="bubble problem">🧩 <b>Problem:</b><br>{st.session_state.problem.replace("\n","<br>")}</div>', unsafe_allow_html=True)
    # student attempt
    st.markdown(f'<div class="bubble student">🧑‍🎓 <b>Initial attempt:</b><br>{st.session_state.student_attempt.replace("\n","<br>")}</div>', unsafe_allow_html=True)
    # tutor initial feedback
    st.markdown(f'<div class="bubble tutor">🤖 <b>Feedback:</b><br>{st.session_state.initial_feedback.replace("\n","<br>")}</div>', unsafe_allow_html=True)

if st.session_state.show_initial_rubric and not st.session_state.initial_rubric_submitted:
    st.markdown("### 🧭 Quick Check on the Initial Feedback")
    st.caption("Please rate the initial feedback you have just received from 1(worst) to 5(best). You will be able to leave some final feedback at the end of the interaction session.")

    st.radio("Relevance – I clearly understand what the tutor is pointing out and it is relevant to the question.",
             [1, 2, 3, 4, 5], key="init_clarity", horizontal=True)
    st.radio("Usefulness – I had a clear idea of what i had missed in my initial solution",
             [1, 2, 3, 4, 5], key="init_actionable", horizontal=True)
    st.radio("Actionability – The feedback gave me easy to follow next steps, targeted to what I missed in my initial solution",
             [1, 2, 3, 4, 5], key="init_focus", horizontal=True)
    st.radio("Coverage – The tutor's feedback adressed all the components of my solution",
             [1, 2, 3, 4, 5], key="init_coverage", horizontal=True)
    st.radio("Conciseness – The tutor's response to my initial solution was clear and readable, with minimal redundancy",
             [1, 2, 3, 4, 5], key="init_conciseness", horizontal=True)

    if st.button("✅ Submit Initial Feedback Evaluation"):
        st.session_state.task_log.setdefault("initial_rubrics", {})
        st.session_state.task_log["initial_rubrics"] = {
            "Relevance": st.session_state.init_clarity,
            "Usefulness": st.session_state.init_actionable,
            "Actionability": st.session_state.init_focus,
            "Coverage": st.session_state.init_coverage,
            "Conciseness": st.session_state.init_conciseness
        }
        st.session_state.initial_rubric_submitted = True
        st.session_state.show_initial_rubric = False
        st.session_state.mode = "main"          # switch to main
        st.rerun()

if st.session_state.get("mode") == "awaiting_first_attempt":
    st.subheader("✍️ Submit Your First Attempt")
    st.markdown(f"**Problem:** {st.session_state.problem}")

    first_attempt = st.text_area("Your one-shot solution:", key="first_attempt")
    
    if st.button("🚀 Submit Initial Attempt") and first_attempt.strip():
        st.session_state.student_attempt = first_attempt.strip()
        st.session_state["attempt_submitted"] = True 

        # Now start the session using the user's typed answer
        initial_feedback, seed_messages = start_session(
            st.session_state.problem,
            st.session_state.student_attempt,
            st.session_state.correct_solution,
            TUTOR_SYSTEM_PROMPT,
            INITIAL_FEEDBACK_TEMPLATE
        )

        st.session_state.api_messages = seed_messages[:]   # copy
        st.session_state.transcript = []
        st.session_state.initial_feedback = initial_feedback
        st.session_state.messages = seed_messages

        st.session_state.task_log = {
            "problem": st.session_state.problem,
            "student_attempt": st.session_state.student_attempt,
            "correct_solution": st.session_state.correct_solution,
            "initial_feedback": st.session_state.initial_feedback,
            "messages": [],
            "similar_problem": st.session_state.similar_problem,
            "similar_solution": st.session_state.similar_solution,
            "followup_response": "",
            "followup_feedback": "",
            "rubrics": {},
            "timestamp": str(datetime.now())
        }

        st.session_state.mode = "initial_feedback"
        st.session_state.task_log["messages"] = [m.copy() for m in st.session_state.transcript]
        st.session_state.show_initial_rubric = True
        st.session_state.initial_rubric_submitted = False
        st.rerun()

if st.session_state.get("mode") == "main":
    for msg in st.session_state.transcript:
        content = msg["content"].replace("\n", "<br>")
        if msg["role"] == "user":
            bubble = f'<div class="bubble student">🧑‍🎓 <b>Student:</b><br>{content}</div>'
        elif msg["role"] == "assistant":
            bubble = f'<div class="bubble tutor">🤖 <b>Tutor:</b><br>{content}</div>'
        st.markdown(bubble, unsafe_allow_html=True)

# -------- Input Interaction --------
def send_and_clear():
    text = st.session_state.student_reply.strip()
    if not text:
        return

    # 1) Append user turn to BOTH
    st.session_state.api_messages.append({"role": "user", "content": text})
    st.session_state.transcript.append({"role": "user", "content": text})

    # 2) Get assistant reply using API messages
    reply = continue_session(st.session_state.api_messages)

    # 3) Append assistant turn to BOTH
    st.session_state.api_messages.append({"role": "assistant", "content": reply})
    st.session_state.transcript.append({"role": "assistant", "content": reply})

    # 4) Save a deep copy to the task_log (so later mutations don’t affect saved data)
    st.session_state.task_log["messages"] = [m.copy() for m in st.session_state.transcript]

    # 5) Clear the input + rerun
    st.session_state.student_reply = ""
    st.rerun()



# -------- Show input during initial and main mode --------
if st.session_state.get("mode") in ["initial_feedback", "main"]:
    if st.session_state.get("mode") == "initial_feedback" and not st.session_state.initial_rubric_submitted:
        st.info("Please complete the quick evaluation above before replying.")
    else:
        st.text_input(
            "✍️ Enter your reply or question to the tutor:",
            key="student_reply"
        )
        st.button("📨 Send Reply", on_click=send_and_clear)


# -------- Finish Phase --------
if st.session_state.get("mode") == "main" and st.session_state.initial_rubric_submitted:
    if st.button("✅ Finish Tutoring / Go to Evaluation"):
        st.session_state.task_log["messages"] = [m.copy() for m in st.session_state.transcript]
        st.session_state.show_rubric = True
        st.session_state.finish_button_clicked = True
        st.session_state.mode = "evaluation"
        st.rerun()

if st.session_state.get("mode") == "evaluation" and st.session_state.get("show_rubric"):
        st.markdown("## 🧪 Evaluate the Tutoring Experience")
        st.markdown(f'<div class="instruction-box">{RUBRIC_INSTRUCTIONS}</div>', unsafe_allow_html=True)

        st.markdown("Rate each from 1 (worst) to 5 (best):")

        st.radio("Diagnostic - the tutor correctly pointed out where and what the errors were in my judgement whenever i shared my own thoughts", [1, 2, 3, 4, 5], key="rubric_diagnostic", horizontal=True)
        st.radio("Correctness - the tutor does not make incorrect statements and is relevant to the current question and my answer", [1, 2, 3, 4, 5], key="rubric_correctness", horizontal=True)
        st.radio("Kept answer hidden - the tutor did not directly reveal the correct answer to me", [1, 2, 3, 4, 5], key="rubric_not_rev", horizontal=True)
        st.radio("Actionability - the tutor gave me sound suggestions/hints that, when followed, have guided me to the correct solution", [1, 2, 3, 4, 5], key="rubric_applicable", horizontal=True)
        st.radio("Positive - the feedback is positive and has an encouraging tone", [1, 2, 3, 4, 5], key="rubric_positive", horizontal=True)

        if st.button("Submit Evaluation / Go to Follow-up"):
            rubric_scores = {
                "Diagnostic": st.session_state.rubric_diagnostic,
                "Correctness": st.session_state.rubric_correctness,
                "Kept answer hidden": st.session_state.rubric_not_rev,
                "Applicable": st.session_state.rubric_applicable,
                "Positive": st.session_state.rubric_positive,
            }

            st.session_state.task_log["rubrics"] = rubric_scores
            st.success("Evaluation Submitted!")
            st.session_state.show_rubric = False
            st.session_state.mode = "followup"
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
        st.session_state.task_log["followup_response"] = one_shot
        st.session_state.task_log["followup_feedback"] = feedback
        st.session_state.task_log["timestamp"] = str(datetime.now())
        st.session_state.show_feedback = True  # trigger display of feedback

    # Display feedback (if already submitted)
    if st.session_state.get("show_feedback"):
        st.markdown("### 🎯 Tutor Feedback:")
        st.success(st.session_state.feedback)
        if not st.session_state.task_completed:
            st.session_state.task_log["messages"] = [m.copy() for m in st.session_state.transcript]
            st.session_state.session_log_data["tasks"].append(st.session_state.task_log)
            st.session_state.task_completed = True

        if st.session_state.task_index < len(TASKS) - 1:
            if st.button("➡️ Go to Next Task"):
                st.session_state.task_index += 1
                st.session_state.mode = "done"  # trigger task reload
                for key in [
                    "problem",
                    "correct_solution",
                    "similar_problem",
                    "similar_solution",
                    "task_log",
                    "messages",
                    "student_reply",
                    "attempt_submitted",
                    "show_feedback",
                    "show_rubric",
                    "student_attempt",
                    "show_initial_rubric","initial_rubric_submitted","initial_feedback"
                ]:
                    if key in st.session_state:
                        del st.session_state[key]

                st.session_state.task_completed = False
                st.rerun()
        else:
            st.markdown("🎉 **All tasks completed! Great job!**")
            st.markdown("### 💬 Additional Comments (optional)")
            st.session_state.additional_comments = st.text_area("Please share here anything you might like to add regarding this study. Did you find it usefull? Did the whole process go smoothly for you?", key="extra_comments")

            def compact(messages):
                # Optional: rename roles for readability
                role_map = {"assistant":"Tutor","user":"Student"}
                return [{"who": role_map.get(m["role"], m["role"]), "text": m["content"]} for m in messages]
            
            def flatten_session_log(log):
                        flat = {
                            "student_id": log["student_id"],
                            "age": log["demographics"].get("age", ""),
                            "gender": log["demographics"].get("gender", ""),
                            "academic_background": log["demographics"].get("academic_background", ""),
                            "academic_level": log["demographics"].get("academic_level", ""),
                        }
                        for i, task in enumerate(log["tasks"]):
                            prefix = f"task_{i+1}_"
                            flat[prefix + "problem"] = task["problem"]
                            flat[prefix + "attempt"] = task["student_attempt"]
                            flat[prefix + "initial_feedback"] = task.get("initial_feedback", "")    
                            flat[prefix + "initial_rubrics"] = json.dumps(task.get("initial_rubrics", {}))
                            clean = compact(task.get("messages", []))
                            flat[prefix + "messages"] = json.dumps(clean, ensure_ascii=False)
                            flat[prefix + "rubrics"] = json.dumps(task.get("rubrics", {}))
                            flat[prefix + "followup_problem"] = task["similar_problem"]
                            flat[prefix + "followup_response"] = task["followup_response"]
                            flat[prefix + "followup_feedback"] = task["followup_feedback"]

                        flat["additional_comments"] = log.get("additional_comments", "")
                        return flat

            if st.button("✅ Submit All & Save"):
                st.session_state.session_log_data["additional_comments"] = st.session_state.get("additional_comments", "")
                final_data = flatten_session_log(st.session_state.session_log_data)
                save_session_to_google_sheet(final_data)
                st.success("All your data has been saved!")


