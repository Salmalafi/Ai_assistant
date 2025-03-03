from flask import Flask, request, jsonify

from config.config import JIRA_URL
from llm_chain.assistant import (
    assistant_create_jira_task,
    assistant_get_issue_details,
    assistant_update_issue,
    assistant_add_comment,
    handle_ask_about_issue, format_issues_response ,get_issues_in_sprint, find_board_id_by_project_name, get_sprints_for_board, generate_sprint_insights, get_sprints_by_state,
format_sprint_issues
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
    - ask_about_sprint
    - add_attachment
    - ask_about_sprint_issues
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
    elif intent=="ask_about_sprint":
        return handle_ask_about_sprint(user_input)
    elif intent=="ask_about_sprint_issues":
        return handle_ask_about_sprint_issues(user_input)
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

def handle_ask_about_sprint(user_input):
    """
    Handle the user's input about sprints.
    This function extracts the project ID, finds the board associated with the project,
    retrieves sprints, and generates insights about those sprints.
    """
    try:
        # Step 1: Extract the project ID from user input (assuming the user provides it in some way)
        # For example, if the user input includes the project name directly
        project_name = extract_project_name_from_input(user_input)

        if not project_name:
            return "Error: Could not extract a valid project name from the input."

        # Step 2: Find the board ID for the project
        board_id = find_board_id_by_project_name(project_name)

        if not board_id:
            return f"Error: No board found for the project '{project_name}'."

        # Step 3: Retrieve sprints for the board
        sprints = get_sprints_for_board(board_id)

        if not sprints:
            return f"No sprints available for the board linked to the project '{project_name}'."

        # Step 4: Generate insights for the retrieved sprints
        sprint_insights = generate_sprint_insights(sprints)

        # Step 5: Format and return the sprint insights
        return sprint_insights

    except Exception as e:
        return f"An error occurred while fetching sprint information: {str(e)}"

def extract_sprint_state_from_input(user_input):
    """
    Extract the sprint state (e.g., 'current', 'future', 'past') from the user's input.

    :param user_input: The user's input as a string.
    :return: Extracted sprint state as a string, or None if no valid sprint state is mentioned.
    """
    try:
        # Possible sprint states
        possible_states = ["current", "future", "past"]

        # Convert the user's input to lowercase for comparison
        user_input_lower = user_input.lower()

        # Check if any of the possible states are mentioned in the input
        for state in possible_states:
            if state in user_input_lower:
                return state

        # If no recognizable sprint state is found, return None
        return None
    except Exception as e:
        return f"An error occurred while extracting sprint state: {str(e)}"


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

def handle_ask_about_sprint_issues(user_input):
    """
    Handles queries about sprint issues based on user input.
    Extracts the project name and sprint state, finds the board and sprint,
    then retrieves and formats the issues in the relevant sprint.

    :param user_input: The input text from the user.
    :return: A formatted string summarizing the issues in the relevant sprint.
    """
    try:
        # Extract the project name and sprint state from the user's input
        project_name = extract_project_name_from_input(user_input)
        sprint_state = extract_sprint_state_from_input(user_input)

        print(f"Project Name Extracted: {project_name}")  # Debugging
        print(f"Sprint State Extracted: {sprint_state}")  # Debugging

        if not project_name:
            return "Error: No project name or ID found in your input."

        if not sprint_state:
            return "Error: No sprint state specified (e.g., current, future, past)."

        # Step 1: Find the board ID for the given project name
        board_id = find_board_id_by_project_name(project_name)
        print(f"Board ID Retrieved: {board_id}")  # Debugging

        if isinstance(board_id, dict) and "error" in board_id:
            return f"Error while finding board: {board_id['error']}"

        # Step 2: Map the user-defined sprint state to Jira's state
        state_mapping = {"current": "active", "future": "future", "past": "closed"}
        jira_state = state_mapping.get(sprint_state)

        print(f"Jira State Mapped: {jira_state}")  # Debugging

        if not jira_state:
            return f"Error: Invalid sprint state '{sprint_state}'. Valid states are: current, future, past."

        # Step 3: Retrieve sprints for the board filtered by state
        sprints = get_sprints_by_state(board_id, jira_state)
        print(f"Sprints Retrieved: {sprints}")  # Debugging

        if not isinstance(sprints, list):  # Ensure `sprints` is a list, otherwise it's an error
            return f"Error: Expected a list of sprints but got {type(sprints).__name__}. Data: {sprints}"

        if not sprints:
            return f"No {sprint_state} sprints found for project '{project_name}'."

        # Step 4: Select the first sprint as the most relevant
        selected_sprint = sprints[0]
        print(f"Selected Sprint: {selected_sprint}")  # Debugging

        sprint_id = selected_sprint.get("id")  # Error could be here if selected_sprint is not a dict
        sprint_name = selected_sprint.get("name")

        if not sprint_id:
            return f"Error: Could not retrieve sprint ID for the sprint '{sprint_name}'."

        # Step 5: Fetch issues for the selected sprint
        issues = get_issues_in_sprint(board_id, sprint_id)
        print(f"Issues Retrieved: {issues}")  # Debugging

        if not isinstance(issues, list):  # Ensure `issues` is a list, otherwise it's an error
            return f"Error: Expected a list of issues but got {type(issues).__name__}. Data: {issues}"

        if not issues:
            return f"No issues found in sprint '{sprint_name}' ({sprint_state})."

        # Step 6: Format the issues for output
        formatted_response = format_sprint_issues(sprint_name, sprint_state, issues)
        return formatted_response

    except Exception as e:
        import traceback
        traceback.print_exc()  # Log the full traceback for debugging
        return f"An error occurred while processing your sprint issue query: {str(e)}"


def extract_project_name_from_input(user_input):
    """
    Extract a project name or project ID from the user's input using natural language understanding.
    For instance, it handles inputs like:
      - "Can you find the sprint information for Project Alpha?"
      - "Show me tasks for project ID PROJ001."

    :param user_input: The user's input as a string.
    :return: Extracted project name or ID as a string, or None if no project is mentioned.
    """
    try:
        # Using natural language extraction to identify project names or IDs
        project_keywords = ["project", "id"]
        project_name = None
        # Break down the user input into words or phrases
        words = user_input.split()
        for i, word in enumerate(words):
            # Check for possible keywords preceding the project name or ID
            if word.lower() in project_keywords:
                if i + 1 < len(words):  # Check if there's a next word
                    project_name = words[i + 1]
                    break
        # Final fallback or validation step
        if project_name:
            return project_name.strip('",.')

        # If no keywords are found, return None
        return None
    except Exception as e:
        print(f"Error while extracting project name: {e}")
        return None


if __name__ == "__main__":
    # Run Flask in a separate thread
    flask_thread = threading.Thread(target=lambda: app.run(debug=True, use_reloader=False))
    flask_thread.daemon = True
    flask_thread.start()

    # Start terminal-based chatbot
    start_terminal_chat()