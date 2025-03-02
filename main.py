from flask import Flask, request, jsonify
from llm_chain.assistant import (
    assistant_create_jira_task,
    assistant_get_issue_details,
    assistant_update_issue,
    assistant_add_comment,
    handle_ask_about_issue, format_issues_response
)
from llm_chain.advanced import (
    assistant_search_issues,
    assistant_assign_issue,
    assistant_transition_issue,
    assistant_add_attachment,
)
from litellm import completion
import re
import threading
import speech_recognition as sr
from flask_cors import CORS

app = Flask(__name__)


def determine_intent(user_input):
    """
    Use an LLM to determine the user's intent.
    Returns only the intent (e.g., "create_task") without additional text.
    """
    prompt = f"""
    Determine the intent of the following user input. Choose from:
    - create_task
    - get_issue_details
    - update_issue
    - add_comment
    - search_issues
    - assign_issue
    - transition_issue
    - add_attachment
    - exit

    Important:
    - Return only the intent (e.g., "create_task") without additional text.
    - Do not include any explanations or prefixes like "the intent of the user input is:".

    User input: {user_input}
    """
    try:
        response = completion(
            model="groq/llama-3.3-70b-versatile",  # Use your preferred LLM
            messages=[{"content": prompt, "role": "user"}],
            api_key="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",
        )
        intent = response.choices[0].message.content.strip()
        intent = intent.lower().replace("the intent of the user input is:", "").strip()
        print(f"Determined Intent: {intent}")  # Debugging
        return intent
    except Exception as e:
        print(f"Error determining intent: {e}")
        return None

def extract_issue_key(user_input):
    """Extract the issue key (e.g., PROJ-123) from the user's input."""
    match = re.search(r"[A-Z]{2,}-\d+", user_input)
    return match.group(0) if match else None


def extract_comment(user_input):
    """Extract the comment from the user's input."""
    match = re.search(r":\s*(.+)", user_input)
    return match.group(1).strip() if match else user_input


def handle_create_task(user_input):
    result = assistant_create_jira_task(user_input)
    return f"Task created: {result}" if result else "Failed to create task."


def handle_get_issue_details(user_input):
    issue_key = extract_issue_key(user_input)
    if issue_key:
        result = assistant_get_issue_details(issue_key)
        return result
    else:
        return "Please specify an issue key (e.g., PROJ-123)."


def handle_update_issue(user_input):
    issue_key = extract_issue_key(user_input)
    if issue_key:
        result = assistant_update_issue(issue_key, user_input)
        return result
    else:
        return "Please specify an issue key (e.g., PROJ-123)."


def handle_add_comment(user_input):
    issue_key = extract_issue_key(user_input)
    if issue_key:
        comment = extract_comment(user_input)
        result = assistant_add_comment(issue_key, comment)
        return result
    else:
        return "Please specify an issue key (e.g., PROJ-123)."


def handle_user_input(user_input):
    intent = determine_intent(user_input)

    if intent == "create_task":
        return handle_create_task(user_input)

    elif intent == "get_issue_details":
        return handle_get_issue_details(user_input)

    elif intent == "update_issue":
        return handle_update_issue(user_input)

    elif intent == "add_comment":
        return handle_add_comment(user_input)


    elif intent == "search_issues":

        result = assistant_search_issues(user_input)

        if isinstance(result, str):  # If an error occurred
            return format_issues_response(result)


    elif intent == "assign_issue":
        result = assistant_assign_issue(user_input)
        return result

    elif intent == "transition_issue":
        result = assistant_transition_issue(user_input)
        return result

    elif intent == "add_attachment":
        result = assistant_add_attachment(user_input)
        return result

    elif intent == "ask_about_issue":
        return handle_ask_about_issue(user_input)

    elif intent == "exit":
        return "Thank you for using the Jira Assistant. Goodbye!"

    else:
        return "Sorry, I didn't understand that. Please try again."



@app.route('/process-input', methods=['POST'])
def process_input():
    """Handle the POST request from the frontend, process the input, and return a response."""
    data = request.get_json()
    user_input = data.get('input')

    if not user_input:
        return jsonify({"response": "No input provided. Please try again."})

    response = handle_user_input(user_input)
    return jsonify({"response": response})


CORS(app, origins=["http://localhost:5173"])


def correct_project_id(transcription):
    """
    Correct common misinterpretations of project IDs in the transcription.
    """
    # Replace common misinterpretations with the correct project ID
    corrections = {
        "are": "RA",
        "our": "RA",
        "are a": "RA",
        "our a": "RA",
    }

    for wrong, correct in corrections.items():
        transcription = re.sub(rf"\b{wrong}\b", correct, transcription, flags=re.IGNORECASE)

    return transcription


def transcribe_live_audio():
    """Capture live audio from the microphone and transcribe it using SpeechRecognition."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio)
        # Correct common misinterpretations of project IDs
        text = correct_project_id(text)
        return text
    except sr.UnknownValueError:
        return "Sorry, I could not understand the audio."
    except sr.RequestError:
        return "Sorry, there was an issue with the speech recognition service."


def start_terminal_chat():
    """Allows chatting in the terminal with voice input."""
    print("Chatbot is running in the terminal. Type 'exit' to quit or say 'voice' to use voice input.")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        elif user_input.lower() == "voice":
            transcription = transcribe_live_audio()
            print(f"You said: {transcription}")
            user_input = transcription  # Use the transcribed text as input

        response = handle_user_input(user_input)
        print("Bot:", response)


if __name__ == "__main__":
    # Run Flask in a separate thread
    flask_thread = threading.Thread(target=lambda: app.run(debug=True, use_reloader=False))
    flask_thread.daemon = True
    flask_thread.start()

    # Start terminal-based chatbot
    start_terminal_chat()