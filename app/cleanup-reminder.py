import gcp.client
import os
import json
import requests
import hmac
from flask import Flask
from flask import request
from flask import jsonify

# Used by Google Cloud library
GOOGLE_APPLICATION_CREDENTIALS_ENV = "GOOGLE_APPLICATION_CREDENTIALS"

GCP_PROJECT_NAME_ENV = "GCP_PROJECT_NAME"
SLACK_BOT_USER_ACCESS_TOKEN_ENV = "SLACK_BOT_USER_ACCESS_TOKEN"
SLACK_SIGNING_SECRET_ENV = "SLACK_SIGNING_SECRET"

URL_VERIFICATION_EVENT_TYPE = "url_verification"
INTERACTIVE_MESSAGE_EVENT_TYPE = "interactive_message"
APP_MENTION_EVENT_TYPE = "app_mention"

SLACK_REQUEST_TIMESTAMP_HEADER = "X-Slack-Request-Timestamp"
SLACK_REQUEST_SIGNATURE_HEADER = "X-Slack-Signature"
SLACK_SIGNING_VERSION = "v0"

gcp_project = os.environ[GCP_PROJECT_NAME_ENV]
bot_access_token = os.environ[SLACK_BOT_USER_ACCESS_TOKEN_ENV]
signing_secret = os.environ[SLACK_SIGNING_SECRET_ENV]

server_port = server = os.environ.get('PORT', 5000)
print(f"PORT: {server_port}")

handled_events = []

app = Flask(__name__)


@app.route("/", methods=['POST', 'GET'])
def core_handler():
    print("Handling request")
    json_data = request.get_json()

    if not is_verified_message_source():
        print("invalid request signature")
        return json.dumps({'error': "invalid request signature"}), 401, {'ContentType': 'application/json'}

    msg_type = json_data["type"]

    if msg_type == URL_VERIFICATION_EVENT_TYPE:
        return handle_url_verification_event(json_data)

    if msg_type == INTERACTIVE_MESSAGE_EVENT_TYPE:
        handle_message_button_submit(json_data)
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

    if "event" not in json_data.keys():
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

    event = json_data["event"]

    if event["type"] == APP_MENTION_EVENT_TYPE:
        event_id = json_data["event_id"]
        handle_app_mention_event(event, event_id)

    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@app.route("/interactive", methods=['POST', 'GET'])
def interactive_handler():
    form_data = request.form

    json_data = json.loads(form_data["payload"])

    msg_type = json_data["type"]

    if msg_type == INTERACTIVE_MESSAGE_EVENT_TYPE:
        return handle_message_button_submit(json_data)

    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


def is_verified_message_source():
    request_timestamp = request.headers.get(SLACK_REQUEST_TIMESTAMP_HEADER)
    raw_body = request.data.decode()

    sign_string = f"{SLACK_SIGNING_VERSION}:{request_timestamp}:{raw_body}"

    computed_hash = hmac_sha256(signing_secret, sign_string)
    full_compare = f"v0={computed_hash}"

    return hmac.compare_digest(request.headers.get(SLACK_REQUEST_SIGNATURE_HEADER), full_compare)


def handle_url_verification_event(json_data):
    print("Handling URL verification")
    if "challenge" in json_data.keys():
        response = {"challenge": json_data["challenge"]}
        return jsonify(response)
    return json.dumps({'success': False}), 400, {'ContentType': 'application/json'}


def handle_message_button_submit(json_data):
    print("Handling interactive button click")

    if json_data["callback_id"] == "delete_cluster":
        actions = json_data["actions"]

        for action in actions:
            print("ACTION: ", action["name"], ": ", action["value"])

        delete_resp = gcp.client.delete_cluster(gcp_project, actions[0]["value"])
        if not delete_resp:
            print("Error deleting cluster: ", delete_resp)

        channel_id = json_data["channel"]["id"]
        original_time_stamp = json_data["original_message"]["ts"]

        gke_clusters = gcp.client.list_clusters(gcp_project)
        message = prepare_message(gke_clusters, gcp_project, channel_id, original_time_stamp)

        print(message)

        headers = get_auth_headers()
        r = requests.post('https://slack.com/api/chat.update', data=json.dumps(message), headers=headers)
        if r.status_code != 200:
            print("Error updating message: ", r)

        return "", 200, {'ContentType': ''}

    return json.dumps({'error': "Failed to handle action"}), 400, {'ContentType': 'application/json'}


def handle_app_mention_event(event, event_id):
    print("Handling app mention event")

    # Events may be sent several times if app take long to spin up
    # Therefor check if this instance already handled specific event
    if event_id in handled_events:
        return

    channel_id = event["channel"]
    gke_clusters = gcp.client.list_clusters(gcp_project)
    message = prepare_message(gke_clusters, gcp_project, channel_id)

    headers = get_auth_headers()
    r = requests.post('https://slack.com/api/chat.postMessage', data=json.dumps(message), headers=headers)

    if r.status_code != 200:
        print("Error posting message to slack.")
    else:
        handled_events.append(event_id)


def prepare_message(gke_clusters, gcp_project, channel_id, time_stamp=0):
    json_msg = {
        "channel": f"{channel_id}",
    }

    if len(gke_clusters) == 0:
        json_msg["text"] = f"No clusters in {gcp_project}!"
        return json_msg

    action_buttons = []
    clusters_list = ""

    for cluster in gke_clusters:
        cluster_name = cluster["name"]
        location = cluster["location"]
        status = cluster["status"]

        action_btn = {
            "name": cluster_name,
            "text": cluster_name,
            "type": "button",
            "value": f"{location}/{cluster_name}"
        }

        clusters_list += f" - `{cluster_name}` - Status: `{status}`\n"

        if status == "RUNNING":
            action_buttons.append(action_btn)

    json_msg = {
        "text": f"There are {len(gke_clusters)} clusters in `{gcp_project}` project.\n"
                f"{clusters_list}"
                f"Remove them if they are no longer needed :)",
        "channel": f"{channel_id}",
        "attachments": [
            {
                "text": "Click button to delete cluster (I am dumb so I can only show 5 buttons)",
                "fallback": "You are unable to choose a game",
                "callback_id": "delete_cluster",
                "color": "#3AA3E3",
                "attachment_type": "default",
                "actions": action_buttons
            }
        ]
    }

    if time_stamp != 0:
        json_msg["ts"] = time_stamp
        json_msg["as_user"] = True

    return json_msg


def get_auth_headers():
    return {'Authorization': f'Bearer {bot_access_token}', 'Content-Type': "application/json; charset=utf-8"}


def hmac_sha256(key, msg):
    key_bytes = str.encode(key)
    msg_bytes = str.encode(msg)

    hash_obj = hmac.new(key=key_bytes, msg=msg_bytes, digestmod="SHA256")
    return hash_obj.hexdigest()


app.run(host='0.0.0.0', debug=False, port=server_port)
