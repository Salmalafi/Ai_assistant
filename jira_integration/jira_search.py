import requests
from requests.auth import HTTPBasicAuth
import json
from config.config import JIRA_EMAIL, JIRA_API_TOKEN, JIRA_URL


# Function to perform a JQL search query
def jql_search(jql_query, max_results=50):
    """
    Executes a JQL query in Jira and returns the issues matching the criteria.

    :param jql_query: The JQL query string to execute
    :param max_results: Maximum number of results to fetch (default 50)
    :return: A list of issues that match the query, or an error message
    """
    url = f"{JIRA_URL}/rest/api/3/search"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # Prepare the request payload
    params = {
        "jql": jql_query,
        "maxResults": max_results,
        "fields": "summary,assignee,priority,status,project"  # Customize fields if needed
    }

    try:
        # Send the GET request with authentication
        response = requests.get(
            url,
            headers=headers,
            params=params,
            auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)  # Basic Auth using your email and API token
        )

        # Check if the request was successful
        if response.status_code == 200:
            # Return the issues in the response
            return response.json()['issues']
        else:
            # If there was an error, return the error message
            return f"Error: {response.status_code} - {response.text}"

    except requests.exceptions.RequestException as e:
        return f"Error executing JQL query: {str(e)}"
