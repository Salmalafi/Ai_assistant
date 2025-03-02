import json
import re
from litellm import completion
from jira_integration.jira_connector import create_jira_issue, get_issue, update_issue, add_comment
from jira_integration.jira_search import jql_search

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
                api_key="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",
            )
            formatted_response = response.choices[0].message.content.strip()
            return formatted_response
        except Exception as e:
            print(f"Error formatting issues response: {e}")
            return "Sorry, I couldn't format the issues. Please try again."