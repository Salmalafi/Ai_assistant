import requests
from requests.auth import HTTPBasicAuth
import json
from config.config import JIRA_EMAIL, JIRA_API_TOKEN, JIRA_URL
from jira_integration.jira_connector import BASE_API_URL, HEADERS

def search_issues(jql_query, max_results=50):
    """
    Search for issues in Jira using a JQL query.

    Args:
        jql_query (str): The JQL query to search for issues.
        max_results (int): Maximum number of results to return (default: 50).

    Returns:
        list: A list of issues matching the query, otherwise None.
    """
    search_url = f"{BASE_API_URL}/search"
    params = {
        "jql": jql_query,
        "maxResults": max_results
    }

    response = requests.get(
        search_url,
        headers=HEADERS,
        params=params,
        auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    )

    if response.status_code == 200:
        return response.json().get("issues", [])
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

def assign_issue(issue_key, assignee_id):
    """
    Assign an issue to a user.

    Args:
        issue_key (str): The Jira issue key (e.g., "FPI-123").
        assignee_id (str): The account ID of the user to assign the issue to.

    Returns:
        bool: True if successful, False otherwise.
    """
    assign_url = f"{BASE_API_URL}/issue/{issue_key}/assignee"
    assign_data = {
        "accountId": assignee_id
    }

    response = requests.put(
        assign_url,
        headers=HEADERS,
        data=json.dumps(assign_data),
        auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    )

    if response.status_code == 204:
        print(f"Issue '{issue_key}' assigned successfully to user '{assignee_id}'.")
        return True
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return False

def transition_issue(issue_key, transition_id):
    """
    Transition an issue to a new status using a transition ID.

    Args:
        issue_key (str): The Jira issue key (e.g., "FPI-123").
        transition_id (str): The ID of the transition to apply.

    Returns:
        bool: True if successful, False otherwise.
    """
    transition_url = f"{BASE_API_URL}/issue/{issue_key}/transitions"
    transition_data = {
        "transition": {
            "id": transition_id
        }
    }

    response = requests.post(
        transition_url,
        headers=HEADERS,
        data=json.dumps(transition_data),
        auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    )

    if response.status_code == 204:
        print(f"Issue '{issue_key}' transitioned successfully.")
        return True
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return False

def get_issue_transitions(issue_key):
    """
    Retrieve available transitions for an issue.

    Args:
        issue_key (str): The Jira issue key (e.g., "FPI-123").

    Returns:
        list: A list of available transitions, otherwise None.
    """
    transitions_url = f"{BASE_API_URL}/issue/{issue_key}/transitions"

    response = requests.get(
        transitions_url,
        headers=HEADERS,
        auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    )

    if response.status_code == 200:
        return response.json().get("transitions", [])
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

def add_attachment(issue_key, file_path):
    """
    Add an attachment to a Jira issue.

    Args:
        issue_key (str): The Jira issue key (e.g., "FPI-123").
        file_path (str): The path to the file to attach.

    Returns:
        dict: The attachment details if successful, otherwise None.
    """
    attachment_url = f"{BASE_API_URL}/issue/{issue_key}/attachments"
    headers = {
        "X-Atlassian-Token": "no-check"
    }

    with open(file_path, "rb") as file:
        response = requests.post(
            attachment_url,
            headers={**HEADERS, **headers},
            files={"file": file},
            auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
        )

    if response.status_code == 200:
        print(f"Attachment added to issue '{issue_key}' successfully.")
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None