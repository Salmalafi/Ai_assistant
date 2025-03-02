
import requests
from requests.auth import HTTPBasicAuth
import json
from config.config import JIRA_EMAIL, JIRA_API_TOKEN, JIRA_URL

# Jira Headers
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# Jira API Base URL
BASE_API_URL = f"{JIRA_URL}/rest/api/3"


def create_jira_issue(project_key, summary, description):
    """
    Create an issue (task) in Jira without an assignee.

    Args:
        project_key (str): The key of the Jira project (e.g., "FPI").
        summary (str): The summary (title) of the issue.
        description (dict): The description of the issue in Atlassian Document Format (ADF).

    Returns:
        dict: The created issue details if successful, otherwise None.
    """
    issue_data = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "description": description,  # Description must be in ADF format
            "issuetype": {"name": "Task"}
        }
    }

    response = requests.post(
        f"{BASE_API_URL}/issue",
        headers=HEADERS,
        data=json.dumps(issue_data),
        auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    )

    if response.status_code == 201:
        print(f"Issue '{summary}' created successfully in Jira.")
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None


def get_issue(issue_key):
    """
    Retrieve issue details from Jira.

    Args:
        issue_key (str): The Jira issue key (e.g., "FPI-123").

    Returns:
        dict: The issue details if found, otherwise None.
    """
    response = requests.get(
        f"{BASE_API_URL}/issue/{issue_key}",
        headers=HEADERS,
        auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    )

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None


def update_issue(issue_key, fields):
    """
    Update an existing Jira issue.

    Args:
        issue_key (str): The Jira issue key (e.g., "FPI-123").
        fields (dict): A dictionary containing fields to update.

    Returns:
        bool: True if successful, False otherwise.
    """
    issue_data = {"fields": fields}

    response = requests.put(
        f"{BASE_API_URL}/issue/{issue_key}",
        headers=HEADERS,
        data=json.dumps(issue_data),
        auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    )

    if response.status_code == 204:
        print(f"Issue '{issue_key}' updated successfully.")
        return True
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return False


def add_comment(issue_key, comment):
    """
    Add a comment to a Jira issue.

    Args:
        issue_key (str): The Jira issue key (e.g., "FPI-123").
        comment (str): The comment text.

    Returns:
        dict: The created comment details if successful, otherwise None.
    """
    comment_data = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": comment}]}
            ]
        }
    }

    response = requests.post(
        f"{BASE_API_URL}/issue/{issue_key}/comment",
        headers=HEADERS,
        data=json.dumps(comment_data),
        auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    )

    if response.status_code == 201:
        print(f"Comment added to issue '{issue_key}' successfully.")
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None
