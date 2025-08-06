import openai
import os
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import json

# Load API key from environment
SPREADSHEET_ID = "1LudHYryIASXAWYaqpsNhjt1HXJQ_2S52D9b_XjtJ2W0"
openai.api_key = os.getenv("OPENAI_API_KEY")

# ----------- MAIN SESSION FUNCTIONS -----------
def provide_initial_feedback(problem, student_sol, correct_solution, initial_feedback_prompt):
    filled_prompt = initial_feedback_prompt.format(
        problem=problem,
        student_sol=student_sol,
        correct_solution=correct_solution
    )
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            { "role": "system", "content": "You are a helpful and supportive discrete math tutor." },
            { "role": "user", "content": filled_prompt }
        ]
    )

    return response.choices[0].message.content

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
        {"role": "user", "content": f"""
                    [PROBLEM]
                    {problem}

                    [STUDENT_ATTEMPT]
                    {student_sol} """
        },
        {"role": "assistant", "content": initial_feedback}
    ]

    return messages


def continue_session(messages):
    response = openai.chat.completions.create(
        model="gpt-4o",
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
        model="gpt-4-turbo",
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

def save_session_to_google_sheet(log_data):
    # Connect to your Google Sheet
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(dict(creds_dict), scopes=scopes)
    client = gspread.authorize(creds)

    sheet = client.open_by_key(SPREADSHEET_ID).sheet1  # or specific worksheet

    # Prepare row as list
    row = [
        log_data["timestamp"],
        log_data["problem"],
        log_data["student_attempt"],
        log_data["correct_solution"],
        json.dumps(log_data["messages"], indent=2),
        log_data["similar_problem"],
        log_data["similar_solution"],
        log_data["followup_response"],
        log_data["followup_feedback"],
        json.dumps(log_data.get("rubrics", {}))
    ]

    sheet.append_row(row)
