import json
import re
from litellm import completion
from requests.auth import HTTPBasicAuth
from jira_integration.jira_connector import create_jira_issue, get_issue, update_issue, add_comment
from jira_integration.jira_search import jql_search
from config.config  import JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN
import requests
# Load API token securely
import os

API_TOKEN = os.getenv("GROQ_API_TOKEN")
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}


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

# Function to convert plain text to Atlassian Document Format (ADF)
def convert_to_adf(text):
    """
    Converts plain text to Atlassian Document Format (ADF).
    """
    return {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": text
                    }
                ]
            }
        ]
    }

# Function to extract JSON from a string
def extract_json_from_string(text):
    """
    Extracts a JSON object from a string using regex.
    Handles nested JSON and malformed JSON.
    """
    # Use regex to find a JSON object in the text
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            # Parse the JSON object
            return json.loads(json_match.group(0))
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")  # Debugging
            return None
    return None

# Function to validate task details
def validate_task_details(task_details):
    """
    Validate task details extracted from the LLM response.
    """
    if not isinstance(task_details, dict):
        return False

    required_keys = ["project_key", "summary", "description"]
    for key in required_keys:
        if key not in task_details or not task_details[key].strip():
            return False
    return True

# Function to create a Jira task
def assistant_create_jira_task(user_input):
    """
    Handle user input, extract task details, and create a Jira issue.
    The LLM generates a better summary and description for the issue.
    """
    # Prepare the prompt for the Groq API
    user_prompt = f"""
    You are a Jira assistant. Your task is to create a Jira issue based on the user's request.
    The user has provided the following input:

    User request: {user_input}

    Based on this input, generate the following details for the Jira issue:
    1. A concise and clear summary (maximum 10 words).
    2. A detailed description of the task (1-2 sentences).

    Return the details in the following JSON format:
    {{
        "project_key": "PROJ",
        "summary": "A concise summary of the task",
        "description": "A detailed description of the task"
    }}

    Example:
    {{
        "project_key": "PROJ",
        "summary": "Implement search functionality",
        "description": "Develop a search feature for the application to allow users to find content quickly and efficiently."
    }}

    Now, generate the JSON for the user's request.
    """

    # Call the Groq API
    response = generate_response_with_groq(user_prompt)

    # Extract JSON from the response
    task_details = extract_json_from_string(response)
    if not task_details:
        print("Error: Failed to extract valid JSON from LLM response.")  # Debugging
        return f"Error: Failed to extract valid JSON from LLM response. Response: {response}"

    print(f"Task details: {task_details}")  # Debugging parsed JSON

    # Validate task details
    if not validate_task_details(task_details):
        print("Error: Insufficient or invalid task details in LLM response.")  # Debugging
        return "Error: Insufficient or invalid task details in LLM response."

    # Extract task details
    project_key = task_details.get("project_key", "").strip()
    summary = task_details.get("summary", "").strip()
    description = task_details.get("description", "").strip()

    # Convert description to ADF
    description_adf = convert_to_adf(description)

    # Create Jira issue using the jira_connector function
    try:
        result = create_jira_issue(project_key, summary, description_adf)
        return f"Jira issue created successfully: {result}"
    except Exception as e:
        print(f"Error creating Jira issue: {e}")  # Debugging
        return f"Error creating Jira issue: {str(e)}"

# Function to retrieve issue details
def assistant_get_issue_details(issue_key):
    """
    Retrieve details of a Jira issue.
    """
    try:
        result = get_issue(issue_key)
        if result:
            return f"Issue details: {json.dumps(result, indent=2)}"
        else:
            return f"Error: Issue '{issue_key}' not found."
    except Exception as e:
        return f"Error retrieving issue details: {str(e)}"

# Function to update a Jira issue
def assistant_update_issue(issue_key, user_input):
    """
    Handle user input, extract update details, and update a Jira issue.
    """
    # Prepare the prompt for the Groq API
    user_prompt = f"""
    Extract the following details from the user request and return them as valid JSON:
    {{
        "summary": "Update search functionality",
        "description": "Enhance the search feature for better performance",
    }}

    User request: {user_input}
    """

    # Call the Groq API
    response = generate_response_with_groq(user_prompt)
    print(f"API Response: {response}")  # Debugging the API response

    # Extract JSON from the response
    update_details = extract_json_from_string(response)
    if not update_details:
        return f"Error: Failed to extract valid JSON from LLM response. Response: {response}"

    print(f"Update details: {update_details}")  # Debugging parsed JSON

    # Extract update details
    summary = update_details.get("summary", "").strip()
    description = update_details.get("description", "").strip()

    # Validate update details
    if not any([summary, description]):
        return "Error: No valid fields to update in LLM response."

    # Prepare fields to update
    fields = {}
    if summary:
        fields["summary"] = summary
    if description:
        fields["description"] = convert_to_adf(description)

    # Update Jira issue using the jira_connector function
    try:
        result = update_issue(issue_key, fields)
        if result:
            return f"Issue '{issue_key}' updated successfully."
        else:
            return f"Error: Failed to update issue '{issue_key}'."
    except Exception as e:
        return f"Error updating Jira issue: {str(e)}"

# Function to add a comment to a Jira issue
def assistant_add_comment(issue_key, comment):
    """
    Add a comment to a Jira issue.
    """
    try:
        result = add_comment(issue_key, comment)
        if result:
            return f"Comment added to issue '{issue_key}' successfully: {json.dumps(result, indent=2)}"
        else:
            return f"Error: Failed to add comment to issue '{issue_key}'."
    except Exception as e:
        return f"Error adding comment to Jira issue: {str(e)}"

# Function to query issues using JQL
def handle_ask_about_issue(user_input):
    """Handle user queries about issues by generating a JQL query and fetching results."""
    # Generate a JQL query using the LLM
    jql_query = generate_jql_query_from_groq(user_input)

    if "Error" in jql_query:
        return jql_query  # Return the error message

    # Execute the JQL query
    issues = jql_search(jql_query)

    if isinstance(issues, str):  # If an error occurred
        return issues
    else:
        return f"Found {len(issues)} issues: {json.dumps(issues, indent=2)}"

# Function to generate a JQL query from Groq
def generate_jql_query_from_groq(user_input):
    """
    Generate a JQL query based on user input using the Groq LLM.
    """
    try:
        # Construct the prompt for Groq to generate the JQL query
        prompt_text = f"Please generate a JQL query for Jira based on the following description: {user_input}"

        # Use the provided `generate_response_with_groq` to get the JQL query from Groq model
        jql_query = generate_response_with_groq(prompt_text)

        # Return the generated JQL query
        return jql_query
    except Exception as e:
        return f"Error generating JQL query: {str(e)}"

def format_issues_response(issues):
        """
        Use the LLM to format a list of issues into a human-readable string.
        """
        if not issues:
            return "No issues found."

        # Convert the list of issues to a JSON string
        issues_json = json.dumps(issues, indent=2)

        # Construct the prompt for the LLM
        prompt = f"""
        You are a Jira assistant. Your task is to format a list of issues into a human-readable response for the user. The issues are provided in JSON format below:

        Issues:
        {issues_json}

        Format the issues into a conversational response. Include the following details for each issue:
        - Key (e.g., RA-123)
        - Summary
        - Assignee (if available)
        - Status
        - Priority (if available)

        Example response:
        "Here are the issues:
        1. RA-123: Fix login bug (Assignee: John Doe, Status: Open, Priority: High)
        2. RA-456: Update documentation (Assignee: Jane Smith, Status: In Progress, Priority: Medium)"

        Now, generate the response for the provided issues.
        """

        try:
            # Call the LLM to generate the formatted response
            response = completion(
                model="groq/llama-3.3-70b-versatile",  # Use your preferred LLM
                messages=[{"content": prompt, "role": "user"}],
                api_key=API_TOKEN,
            )
            formatted_response = response.choices[0].message.content.strip()
            return formatted_response
        except Exception as e:
            print(f"Error formatting issues response: {e}")
            return "Sorry, I couldn't format the issues. Please try again."
def find_board_id_by_project_name(project_name):
    """
    Find the board ID using the project name by filtering boards with query parameters.

    :param project_name: The project name to search for (filters board by name).
    :return: The ID of the board associated with the project name, or an error message.
    """
    try:
        # URL to fetch boards with filtering by name
        url = f"{JIRA_URL}/rest/agile/1.0/board"
        # Passing the name as a query parameter to filter results
        params = {"name": project_name}

        # Make the request to Jira API
        response = requests.get(url, headers=HEADERS, params=params ,  auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN))

        if response.status_code == 200:
            # Parse the response
            boards = response.json().get("values", [])
            if not boards:
                return f"Error: No board found for the project '{project_name}'."

            # Return the ID of the first matching board
            return boards[0]["id"]

        elif response.status_code == 401:
            return "Error: Unauthorized. Check your API token and email credentials."

        else:
            return f"Error fetching boards: {response.status_code}. Details: {response.text}"

    except Exception as e:
        return f"Error while finding board ID: {str(e)}"

# Function to debug network request
def debug_request(url, headers, params=None):
    """
    Print the details of the request for debugging.
    """
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    if params:
        print(f"Query Parameters: {params}")

# Function to retrieve sprints for a specific board
def get_sprints_for_board(board_id):
    """
    Retrieve sprints for the specified board ID.
    """
    url = f"{JIRA_URL}/rest/agile/1.0/board/{board_id}/sprint"

    response = requests.get(url,  headers=HEADERS,  auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN))
    if response.status_code == 200:
        sprints = response.json().get("values", [])
        return sprints  # List of sprints
    elif response.status_code == 401:
        print("Error: Unauthorized. Check your credentials.")
        return []
    else:
        print(f"Error fetching sprints: {response.status_code}. Details: {response.text}")
        return []
# Function to generate insights from retrieved sprints
def generate_sprint_insights(sprints):
    """
    Generate well-formatted insights for the retrieved sprints in bullet point format.
    """
    if not sprints:
        return "No sprints available."

    insights = []
    for sprint in sprints:
        # Extract relevant details with defaults
        name = sprint.get("name", "Unknown")
        state = sprint.get("state", "Unknown")  # e.g., active, closed, future
        start_date = sprint.get("startDate", "N/A")
        end_date = sprint.get("endDate", "N/A")
        complete_date = sprint.get("completeDate", "N/A")

        # Create a formatted string for the sprint
        insight = (
            f"- **Sprint Name**: {name}\n"
            f"  - **State**: {state}\n"
            f"  - **Start Date**: {start_date}\n"
            f"  - **End Date**: {end_date}\n"
            f"  - **Complete Date**: {complete_date}\n"

        )
        insights.append(insight)

    # Combine all insights into a single string
    return "\n".join(insights)

def get_sprints_by_state(board_id, states):
    """
    Retrieve sprints for a given board ID filtered by specified state(s).

    :param board_id: The ID of the board linked to the project.
    :param states: A comma-separated string of sprint states, e.g., "active", "future", "closed".
    :return: A list of sprints based on the state(s) provided, or an error message if no matching sprints are found.
    """
    try:
        # URL for fetching sprints based on state
        url = f"{JIRA_URL}/rest/agile/1.0/board/{board_id}/sprint"
        params = {"state": states}  # Query parameter for sprint states
        response = requests.get(url, headers=HEADERS, params=params ,  auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN))

        if response.status_code == 200:
            sprints = response.json().get("values", [])
            if not sprints:
                return f"No sprints found for the given state(s): {states}."

            return sprints

        elif response.status_code == 401:
            return "Error: Unauthorized. Check your API token and email credentials."

        else:
            return f"Error fetching sprints: {response.status_code}. Details: {response.text}"

    except Exception as e:
        return f"Error while fetching sprints by state: {str(e)}"


def get_issues_by_sprint_state(project_name, sprint_state):
    """
    Retrieve issues for a sprint in a given project dynamically based on sprint state.

    :param project_name: The name of the project to retrieve the board and sprint from.
    :param sprint_state: The state of the sprint to fetch (e.g., "current", "future", "past").
    :return: A formatted string summarizing the issues found in the filtered sprint, or an error message.
    """
    try:
        # Step 1: Map user-friendly sprint state to valid Jira API states
        state_mapping = {
            "current": "active",
            "future": "future",
            "past": "closed"
        }
        jira_state = state_mapping.get(sprint_state.lower(), "active")  # Default to "active"

        # Step 2: Get the Board ID from the Project Name
        board_id = find_board_id_by_project_name(project_name)
        if isinstance(board_id, str):  # Catch error messages
            return board_id

        # Step 3: Get Sprints for the Board by State
        sprints = get_sprints_by_state(board_id, jira_state)
        if isinstance(sprints, str):  # Catch error messages
            return sprints

        # Step 4: Retrieve Issues for the First Matched Sprint
        selected_sprint = sprints[0] if sprints else None
        if not selected_sprint:
            return f"No sprints found with the state '{sprint_state}'."

        sprint_id = selected_sprint["id"]
        sprint_name = selected_sprint["name"]

        # Fetch issues for the selected sprint
        issues = get_issues_in_sprint(sprint_id, board_id)
        if isinstance(issues, str):  # Catch error messages
            return issues

        # Step 5: Format issues for better readability
        formatted = [f"**Sprint Name**: {sprint_name} ({sprint_state.capitalize()})\n"]
        for issue in issues:
            formatted.append(
                f"- **{issue['Key']}**: {issue['Summary']}\n"
                f"  - Status: {issue['Status']}\n"
                f"  - Assignee: {issue['Assignee']}\n"
            )
        return "\n".join(formatted)

    except Exception as e:
        return f"Error while fetching issues by sprint state: {str(e)}"

def get_issues_in_sprint(boardid, sprintid):
    """
    Retrieves issues from a specific sprint using the board ID and sprint ID.

    :param boardid: The ID of the board associated with the sprint.
    :param sprintid: The ID of the sprint from which to fetch issues.
    :return: A list of issues in the sprint or an error message.
    """
    try:
        # Step 1: Validate parameters
        if not boardid or not sprintid:
            return "Error: Both board ID and sprint ID are required to fetch issues."

        # Step 2: Construct the URL for the Jira API
        url = f"{JIRA_URL}/rest/agile/1.0/sprint/{sprintid}/issue"

        # Step 3: Make the HTTP GET request
        response = requests.get(
            url,
            headers=HEADERS,
            auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
        )

        # Check for HTTP errors
        if response.status_code != 200:
            return f"Error: Unable to fetch issues. HTTP Status: {response.status_code}, Response: {response.text}"

        # Parse JSON response
        response_data = response.json()
        issues = response_data.get("issues", [])
        print(f"Raw Issues Data: {issues}")  # Debugging

        if not issues:
            return f"No issues found for sprint ID '{sprintid}' on board ID '{boardid}'."

        # Format and return issues
        formatted_issues = []
        for issue in issues:
            if not issue or not isinstance(issue, dict):  # Handle invalid issue data
                formatted_issues.append({
                    "Key": "Invalid Issue",
                    "Summary": "Invalid Issue Data",
                    "Status": "Invalid",
                    "Assignee": "Unknown"
                })
                continue

            fields = issue.get("fields", {})  # Safe access for 'fields'
            status = fields.get("status", {})  # Safe access for 'status'
            assignee = fields.get("assignee", {})  # Safe access for 'assignee'

            formatted_issues.append({
                "Key": issue.get("key", "Unknown Issue Key"),
                "Summary": fields.get("summary", "No Summary Available"),
                "Status": status.get("name", "Unknown Status"),
                "Assignee": assignee.get("displayName", "Unassigned")
            })

        return formatted_issues

    except Exception as e:
        import traceback
        traceback.print_exc()  # Optional: Print full traceback for debugging
        return f"An error occurred while fetching issues in sprint: {str(e)}"


def format_sprint_issues(sprint_name, sprint_state, issues):
    """
    Formats a list of sprint issues into a human-readable string.

    :param sprint_name: Name of the sprint.
    :param sprint_state: State of the sprint (e.g., current, future, past).
    :param issues: List of issues with their details (Key, Summary, Status, Assignee).
    :return: A formatted string summarizing the issues.
    """
    output = [f"**Sprint Name**: {sprint_name} ({sprint_state.capitalize()})",
              "=================================================="]

    for issue in issues:
        output.append(f"- **{issue['Key']}**: {issue['Summary']}")
        output.append(f"  - **Status**: {issue['Status']}")
        output.append(f"  - **Assignee**: {issue['Assignee']}")
        output.append("--------------------------------------------------")

    return "\n".join(output)


def get_issues_assigned_to_me():
    """
    Retrieves Jira issues assigned to the current user using JQL query.
    :return: A list of issues assigned to the user or an error message.
    """
    try:
        # Construct the JQL query
        jql_query = f"assignee = \"{JIRA_EMAIL}\""

        # Jira API URL - search endpoint
        url = f"{JIRA_URL}/rest/api/3/search"

        # API parameters
        params = {
            "jql": jql_query,
            "fields": "key,summary,status,priority,duedate",  # Fetch only required fields
            "maxResults": 100
        }

        # Send the GET request
        response = requests.get(url, headers=HEADERS, params=params,
                                auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN))
        # Check if the request was successful
        if response.status_code != 200:
            return {
                "success": False,
                "message": f"Error: HTTP {response.status_code}, Response: {response.text}",
                "tasks": []
            }
        # Safely parse the response
        response_data = response.json()  # Will raise exception if not valid JSON
        issues = response_data.get("issues", [])  # Default to empty list if "issues" doesn't exist
        # Ensure issues is a list
        if not isinstance(issues, list):
            return {
                "success": False,
                "message": "Invalid response format. 'issues' is not a list.",
                "tasks": []
            }
        # Process and format issues
        formatted_issues = []
        for issue in issues:
            fields = issue.get("fields", {})
            formatted_issues.append({
                "issue_key": issue.get("key", "N/A"),
                "summary": fields.get("summary", "No Summary"),
                "status": fields.get("status", {}).get("name", "Unknown"),
                "priority": fields.get("priority", {}).get("name", "No Priority"),
                "due_date": fields.get("duedate", "No Due Date")
            })
        # Return successfully retrieved tasks
        return {
            "success": True,
            "message": "Tasks successfully retrieved.",
            "tasks": formatted_issues
        }

    except Exception as e:
        # Handle any unexpected failures
        return {
            "success": False,
            "message": f"An error occurred while retrieving tasks: {str(e)}",
            "tasks": []
        }


def extract_assignee_name(user_input):
    """
    Extracts the assignee's name from the user's input.
    :param user_input: The input text from the user.
    :return: The extracted name of the assignee, if found.
    """
    # Example logic: Look for the phrase "to <name>" in the input
    if " to " in user_input:
        return user_input.split(" to ")[-1].strip()

    # If "to" isn't present, assume no assignee was mentioned
    return None

def assign_issue_to_user(issue_key, assignee_name):
    """
    Assigns an issue to a user in the system using the Jira API.

    Args:
        issue_key (str): The unique identifier of the issue to be assigned.
        assignee_name (str): The name of the user to whom the issue will be assigned.

    Returns:
        str: A message indicating whether the assignment was successful or not.
    """
    try:
        # Find the assignee's account ID
        assignee_account_id = get_assignee_account_id(assignee_name)
        if not assignee_account_id:
            return f"User '{assignee_name}' not found in the system. Please check the name and try again."

        # Jira API endpoint for assigning tasks
        url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}/assignee"

        # Payload for assigning the task
        payload = {"accountId": assignee_account_id}

        # Make the API request to assign the issue
        response = requests.put(
            url,
            headers=HEADERS,
            json=payload,
            auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
        )

        # Handle the Jira API response
        if response.status_code == 204:
            return f"Issue '{issue_key}' successfully assigned to '{assignee_name}'."
        else:
            return f"Failed to assign issue '{issue_key}'. API returned error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"An unexpected error occurred while assigning the task: {str(e)}"


def get_assignee_account_id(assignee_name):
    """
    Resolves a user's Atlassian account ID based on their display name using the Jira API.


    Args:
        assignee_name (str): The display name of the user.

    Returns:
        str: The account ID of the user if found, or None if the user does not exist.
    """
    try:
        # Jira API endpoint to search for users
        url = f"{JIRA_URL}/rest/api/3/user/search"
        params = {"query": assignee_name}

        # Send the GET request to search for the user
        response = requests.get(
            url,
            headers=HEADERS,
            params=params,
            auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
        )
        # Validate the response
        if response.status_code == 200:
            users = response.json()
            for user in users:
                # Compare displayNames (case-insensitive)
                if user.get("displayName", "").lower() == assignee_name.lower():
                    return user.get("accountId")  # Return the account ID of the user
            return None  # No matching user found
        else:
            print(f"[ERROR] Failed to fetch user data: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"[ERROR] An error occurred while resolving user account ID: {e}")
        return None

def validate_assignee(assignee_name):
    """
    Validates if the assignee exists in the Jira system.

    Args:
        assignee_name (str): The assignee's name to validate.

    Returns:
        bool: True if the assignee is valid/existing in the system, False otherwise.
    """
    try:
        # Jira API endpoint to search for users
        url = f"{JIRA_URL}/rest/api/3/user/search"
        params = {"query": assignee_name}  # Search query (Jira matches on display name, email, etc.)

        # Perform the GET request to search for the user
        response = requests.get(
            url,
            headers=HEADERS,
            params=params,
            auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
        )
        # Check if the response is successful
        if response.status_code == 200:
            users = response.json()
            for user in users:
                # Compare displayNames (case-insensitive search)
                if user.get("displayName", "").lower() == assignee_name.lower():
                    return True  # User found in the system
            return False  # No matching user found
        else:
            print(f"[ERROR] Failed to fetch user data: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] An error occurred during user validation: {e}")
        return False

def get_issue_key_from_jira(description):
    """
    Retrieves the issue key from Jira based on the issue description or other fields.

    Args:
        description (str): The keywords or text to search for in Jira.

    Returns:
        str: The issue key if found, or None if no matching issue is found.
    """
    # Escape double quotes in the description to avoid JQL syntax issues
    description = description.replace('"', '\\"')

    # Define the JQL query
    query = {
        "jql": f'text ~ "{description}"',  # Match any indexed field (summary, description, etc.)
        "fields": ["key", "summary", "description"],  # Retrieve specific fields
        "maxResults": 1,  # Fetch only one result
    }
    # Jira Search API URL
    url = f"{JIRA_URL}/rest/api/3/search"  # Replace JIRA_URL with your Jira instance base URL
    try:
        # Send the POST request to Jira's search endpoint
        response = requests.post(
            url,
            headers=HEADERS,  # Ensure HEADERS includes valid Authorization and Content-Type
            json=query,  # Send JSON payload
            auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN),  # Jira Email and API Token for authentication
        )

        # Raise an HTTP error if one occurred
        response.raise_for_status()

        # Parse the response JSON
        data = response.json()
        print(f"API Response: {data}")  # Debugging: View the entire response

        # Check if any issues were returned
        issues = data.get("issues", [])
        if issues:
            # Get the key of the first matching issue
            issue = issues[0]
            issue_key = issue.get("key")
            print(f"Found Issue: Key = {issue_key}")
            return issue_key

        # No matching issues found
        print("No issues matched the given query.")
        return None

    except requests.exceptions.RequestException as e:
        # Handle errors (HTTP or connection issues)
        print(f"Error fetching data from Jira: {e}")
        return None
