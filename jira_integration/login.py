from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS
import requests

app = Flask(__name__)

# Enable CORS for all routes, allowing requests from http://localhost:5173
CORS(app, origins=["http://localhost:5173"])

@app.route('/login', methods=['POST'])
def login():
    # Get credentials from the request
    data = request.json
    email = data.get('email')
    api_token = data.get('api_token')
    jira_url = data.get('jira_url')

    if not email or not api_token or not jira_url:
        return jsonify({"error": "Missing email, API token, or Jira URL"}), 400

    # Call Jira API to authenticate the user
    auth = (email, api_token)
    headers = {"Accept": "application/json"}
    jira_api_url = f"{jira_url}/rest/api/3/myself"

    try:
        response = requests.get(jira_api_url, headers=headers, auth=auth)

        if response.status_code == 200:
            user_data = response.json()
            return jsonify({
                "message": "Authentication successful",
                "user": user_data
            }), 200
        else:
            return jsonify({
                "error": "Authentication failed",
                "status_code": response.status_code,
                "details": response.text
            }), 401

    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": "Failed to connect to Jira",
            "details": str(e)
        }), 500

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)