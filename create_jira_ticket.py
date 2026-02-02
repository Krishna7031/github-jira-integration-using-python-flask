from flask import Flask
import requests
from requests.auth import HTTPBasicAuth
import json

#Creating a flask application instance
app = Flask(__name__)

@app.route("/createJIRA", methods=["POST"])
def create_JIRA():
    url = "https://krishnasworkspace-40289487.atlassian.net//rest/api/3/issue"

    API_TOKEN = ""

    auth = HTTPBasicAuth("krishna70310@gmail.com", API_TOKEN)

    headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
    }

    payload = json.dumps( {
    "fields": {
        "description": {
        "content": [
            {
            "content": [
                {
                "text": "My first jira ticket",
                "type": "text"
                }
            ],
            "type": "paragraph"
            }
        ],
        "type": "doc",
        "version": 1
        },
        "issuetype": {
        "name": "Story"
        },
        "project": {
        "key": "PROJ"
        },
        "summary": "First JIRA Ticket",
    },
    "update": {}
    } )

    response = requests.request(
    "POST",
    url,
    data=payload,
    headers=headers,
    auth=auth
    )

    return json.dumps(json.loads(response.text), sort_keys=True, indent=4, separators=(",", ": "))

app.run(host="0.0.0.0", port=5000)
