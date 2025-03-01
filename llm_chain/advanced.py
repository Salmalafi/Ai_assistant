import json
import re
from litellm import completion
from jira_integration.jira_advanced import (
    search_issues,
    assign_issue,
    transition_issue,
    get_issue_transitions,
    add_attachment,
)

# Load API token securely
API_TOKEN = "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"

# Function to call Groq API for text generation using LiteLLM
def generate_response_with_groq(prompt_text):
    try:
        response = completion(
            model="groq/llama-3.3-70b-versatile",  # Model name for Groq
            messages=[{"content": prompt_text, "role": "user"}],
            api_key=API_TOKEN,
        )
        # Extract the generated text from the response
        generated_text = response.choices[0].message.content
        return generated_text.strip()
    except Exception as e:
        return f"API Error: {str(e)}"

# Function to extract JSON from a string
def extract_json_from_string(text):
    """
    Extracts a JSON object from a string using regex.
    """
    # Use regex to find a JSON object in the text
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            # Parse the JSON object
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            return None
    return None

# Function to handle searching for issues
def assistant_search_issues(user_input):
    """
    Handle user input, extract JQL query, and search for issues.
    """
    # Prepare the prompt for the Groq API
    user_prompt = f"""
    Extract the following details from the user request and return them as valid JSON:
    {{
        "jql_query": "project = PROJ AND status = 'In Progress'"
    }}

    User request: {user_input}
    """

    # Call the Groq API
    response = generate_response_with_groq(user_prompt)
    print(f"API Response: {response}")  # Debugging the API response

    # Extract JSON from the response
    search_details = extract_json_from_string(response)
    if not search_details:
        return f"Error: Failed to extract valid JSON from LLM response. Response: {response}"

    print(f"Search details: {search_details}")  # Debugging parsed JSON

    # Extract JQL query
    jql_query = search_details.get("jql_query", "").strip()

    # Validate JQL query
    if not jql_query:
        return "Error: No valid JQL query found in LLM response."

    # Search for issues using the jira_advanced function
    try:
        issues = search_issues(jql_query)
        if issues:
            return f"Found {len(issues)} issues: {json.dumps(issues, indent=2)}"
        else:
            return "No issues found matching the query."
    except Exception as e:
        return f"Error searching for issues: {str(e)}"

# Function to handle assigning an issue
def assistant_assign_issue(user_input):
    """
    Handle user input, extract issue key and assignee ID, and assign the issue.
    """
    # Prepare the prompt for the Groq API
    user_prompt = f"""
    Extract the following details from the user request and return them as valid JSON:
    {{
        "issue_key": "PROJ-123",
        "assignee_id": "5f9b5b5b5b5b5b5b5b5b5b5b"
    }}

    User request: {user_input}
    """

    # Call the Groq API
    response = generate_response_with_groq(user_prompt)
    print(f"API Response: {response}")  # Debugging the API response

    # Extract JSON from the response
    assign_details = extract_json_from_string(response)
    if not assign_details:
        return f"Error: Failed to extract valid JSON from LLM response. Response: {response}"

    print(f"Assign details: {assign_details}")  # Debugging parsed JSON

    # Extract issue key and assignee ID
    issue_key = assign_details.get("issue_key", "").strip()
    assignee_id = assign_details.get("assignee_id", "").strip()

    # Validate inputs
    if not all([issue_key, assignee_id]):
        return "Error: Insufficient details in LLM response."

    # Assign the issue using the jira_advanced function
    try:
        result = assign_issue(issue_key, assignee_id)
        if result:
            return f"Issue '{issue_key}' assigned successfully to user '{assignee_id}'."
        else:
            return f"Error: Failed to assign issue '{issue_key}'."
    except Exception as e:
        return f"Error assigning issue: {str(e)}"

# Function to handle transitioning an issue
def assistant_transition_issue(user_input):
    """
    Handle user input, extract issue key and transition ID, and transition the issue.
    """
    # Prepare the prompt for the Groq API
    user_prompt = f"""
    Extract the following details from the user request and return them as valid JSON:
    {{
        "issue_key": "PROJ-123",
        "transition_id": "21"
    }}

    User request: {user_input}
    """

    # Call the Groq API
    response = generate_response_with_groq(user_prompt)
    print(f"API Response: {response}")  # Debugging the API response

    # Extract JSON from the response
    transition_details = extract_json_from_string(response)
    if not transition_details:
        return f"Error: Failed to extract valid JSON from LLM response. Response: {response}"

    print(f"Transition details: {transition_details}")  # Debugging parsed JSON

    # Extract issue key and transition ID
    issue_key = transition_details.get("issue_key", "").strip()
    transition_id = transition_details.get("transition_id", "").strip()

    # Validate inputs
    if not all([issue_key, transition_id]):
        return "Error: Insufficient details in LLM response."

    # Transition the issue using the jira_advanced function
    try:
        result = transition_issue(issue_key, transition_id)
        if result:
            return f"Issue '{issue_key}' transitioned successfully."
        else:
            return f"Error: Failed to transition issue '{issue_key}'."
    except Exception as e:
        return f"Error transitioning issue: {str(e)}"

# Function to handle adding an attachment
def assistant_add_attachment(user_input):
    """
    Handle user input, extract issue key and file path, and add an attachment.
    """
    # Prepare the prompt for the Groq API
    user_prompt = f"""
    Extract the following details from the user request and return them as valid JSON:
    {{
        "issue_key": "PROJ-123",
        "file_path": "/path/to/file.txt"
    }}

    User request: {user_input}
    """

    # Call the Groq API
    response = generate_response_with_groq(user_prompt)
    print(f"API Response: {response}")  # Debugging the API response

    # Extract JSON from the response
    attachment_details = extract_json_from_string(response)
    if not attachment_details:
        return f"Error: Failed to extract valid JSON from LLM response. Response: {response}"

    print(f"Attachment details: {attachment_details}")  # Debugging parsed JSON

    # Extract issue key and file path
    issue_key = attachment_details.get("issue_key", "").strip()
    file_path = attachment_details.get("file_path", "").strip()

    # Validate inputs
    if not all([issue_key, file_path]):
        return "Error: Insufficient details in LLM response."

    # Add the attachment using the jira_advanced function
    try:
        result = add_attachment(issue_key, file_path)
        if result:
            return f"Attachment added to issue '{issue_key}' successfully."
        else:
            return f"Error: Failed to add attachment to issue '{issue_key}'."
    except Exception as e:
        return f"Error adding attachment: {str(e)}"