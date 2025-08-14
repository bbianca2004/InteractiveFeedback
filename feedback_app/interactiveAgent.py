import openai
import os
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import json

from feedback_app.prompts import INITIAL_FEEDBACK_SYSTEM_PROMPT

# Load API key from environment
SPREADSHEET_ID = "1LudHYryIASXAWYaqpsNhjt1HXJQ_2S52D9b_XjtJ2W0"
openai.api_key = os.getenv("OPENAI_API_KEY")

# ----------- MAIN SESSION FUNCTIONS -----------
def provide_initial_feedback(problem, student_sol, correct_solution, initial_feedback_prompt):
    student_clean = (student_sol or "").strip().lower()
    low_info = (len(student_clean) < 20) or student_clean in {"", "hmm", "idk", "?", "i don't know", "na"}

    system_msg = INITIAL_FEEDBACK_SYSTEM_PROMPT

    if low_info:
                # Even stricter instructions for empty attempts
                user_template = """Problem:
        {problem}

        Student wrote EXACTLY:
        <<<
        {student_sol}
        >>>

        Official Solution (use only to guide hints; NEVER reveal it):
        {correct_solution}

        The student provided no substantive attempt. Do NOT critique non-existent steps.
        - Say you can't evaluate yet because there are no steps.
        - Give 1–2 concrete starter hints or guiding questions (tiny, not revealing).
        - Invite them to try an attempt."""
    else:
        user_template = initial_feedback_prompt

    filled = user_template.format(
        problem=problem,
        student_sol=student_sol,
        correct_solution=correct_solution
    )

    # resp = openai.chat.completions.create(
    #     model="gpt-5",
    #     temperature=0.2,      # reduce “creative guessing”
    #     top_p=0.2,
    #     presence_penalty=0.0,
    #     messages=[
    #         {"role": "system", "content": system_msg},
    #         {"role": "user", "content": filled},
    #     ],
    # )

    resp = openai.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": filled},
        ],
    )
    return resp.choices[0].message.content

def start_session(problem, student_sol, correct_solution, system_prompt, initial_feedback_prompt):
    # Generate initial feedback
    initial_feedback = provide_initial_feedback(problem, student_sol, correct_solution, initial_feedback_prompt)

    tutoring_context = f"""
        You are an AI math tutor helping a student. Here is the problem, their attempt, and the correct solution:

        [PROBLEM]
        {problem}
        [/PROBLEM]

        [STUDENT_ATTEMPT]
        {student_sol}
        [/STUDENT_ATTEMPT]

        [OFFICIAL_SOLUTION]
        {correct_solution}
        [/OFFICIAL_SOLUTION]

        Begin tutoring by asking clarifying questions. Do NOT reveal the correct solution directly.
        Instead, use it internally to guide the student with subtle, progressive hints.
    """

    messages = [
        {"role": "system", "content": system_prompt + "\n" + tutoring_context},
        {"role": "assistant", "content": initial_feedback}
    ]

    return initial_feedback, messages


def continue_session(messages):
    response = openai.chat.completions.create(
        model="gpt-5",
        messages=messages
    )
    return response.choices[0].message.content

# ----------- FOLLOW-UP EVALUATION -----------

def evaluate_followup(problem, student_response, correct_solution, evaluation_prompt):
    filled_prompt = evaluation_prompt.format(
        statement = problem.strip(),
        solution=correct_solution.strip(),
        student_response=student_response.strip()
    )

    response = openai.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "system", "content": "You are an objective math tutor evaluating student answers."},
            {"role": "user", "content": filled_prompt}
        ]
    )

    return response.choices[0].message.content

# ----------- LOGGING -----------

def save_session_log(problem, student_attempt, correct_solution, messages, tag=None, notes=None):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_dir = "tutoring_logs"
    os.makedirs(log_dir, exist_ok=True)
    filename = os.path.join(log_dir, f"session_{timestamp}.txt")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("=== Main Tutoring Session ===\n")
        f.write(f"Problem: {problem}\n\n")
        f.write(f"Student Attempt: {student_attempt}\n\n")
        f.write(f"Correct Solution: {correct_solution}\n\n")
        f.write("Dialogue:\n")
        for msg in messages:
            role = "GPT" if msg["role"] == "assistant" else "Student"
            f.write(f"{role}: {msg['content']}\n\n")

        if tag or notes:
            f.write("\n=== Researcher Annotation ===\n")
            if tag:
                f.write(f"Tag: {tag}\n")
            if notes:
                f.write(f"Notes: {notes}\n")

    print(f"Main session saved to {filename}")

def save_followup_log(problem, student_response, correct_solution, feedback):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_dir = "checkup_logs"
    os.makedirs(log_dir, exist_ok=True)
    filename = os.path.join(log_dir, f"followup_{timestamp}.txt")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("=== Similar Problem Evaluation ===\n")
        f.write(f"Problem: {problem}\n\n")
        f.write(f"Student Response: {student_response}\n\n")
        f.write(f"Correct Solution: {correct_solution}\n\n")
        f.write(f"GPT Feedback:\n{feedback}\n")

    print(f"Follow-up log saved to {filename}")

def save_session_to_google_sheet(data):
    # Connect to your Google Sheet
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(dict(creds_dict), scopes=scopes)
    client = gspread.authorize(creds)

    sheet = client.open_by_key(SPREADSHEET_ID).sheet1  # or specific worksheet

    if sheet.row_count == 0 or sheet.cell(1, 1).value == "":
        sheet.append_row(list(data.keys()))

    sheet.append_row(list(data.values()))



