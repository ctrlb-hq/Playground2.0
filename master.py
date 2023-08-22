from flask import Flask, render_template, request, redirect, jsonify
from flask_cors import CORS
from flask_pymongo import PyMongo, MongoClient
from pymongo.errors import OperationFailure
from urllib.parse import quote_plus
import subprocess
import time
import os
import threading
import requests
import websockets
import asyncio
import json
from datetime import datetime
import pytz
import secrets
import string
import os
from dotenv import load_dotenv
from database import Database
from datetime import datetime


# Load environment variables from the .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Replace <YOUR_USERNAME> and <YOUR_PASSWORD> with your MongoDB Atlas credentials
username = os.getenv("DB_USERNAME")
password = os.getenv("DB_PASSWORD")
cluster_name = os.getenv("DB_CLUSTER")
dbname = os.getenv("DB_NAME")
start_port = int(os.getenv("START_PORT"))
end_port = int(os.getenv("END_PORT"))
kill_child_process_in_seconds = int(os.getenv("KILL_CHILD_PROCESS_IN_SECONDS"))
sleep_watcher_for_seconds = int(os.getenv("SLEEP_WATCHER_FOR_SECONDS"))

# Escape the username and password using urllib.parse.quote_plus
escaped_username = quote_plus(username)
escaped_password = quote_plus(password)
mongo_uri = f"mongodb+srv://{username}:{password}@{cluster_name}/{dbname}?retryWrites=true&w=majority"

app.config["MONGO_URI"] = mongo_uri
try:
    # Connect to MongoDB using the configured URI
    mongo_client = MongoClient(mongo_uri)
    db = mongo_client["CtrlB-Playground"]  # Get the default database
    collection = db[dbname]  # Use the "entries" collection for storing entries
    print(f"Connected to MongoDB Atlas successfully at cluster: {cluster_name}/{dbname}")
except OperationFailure as e:
    print("Failed to connect to MongoDB Atlas:")
    print(f"Error message: {e.details['errmsg']}")
    print(f"Error code: {e.details['code']}")
    print(f"Error code name: {e.details['codeName']}")

# Flag to signal the port_watcher thread to stop
stop_port_watcher = False
database = Database()

# Outside of any function, at the beginning of your script
tracepoint_events_by_port = {}  # {port: [live_message1, live_message2, ...]}

def add_email_in_persistent_db(email):
    # Check if the email exists in the collection
    existing_entry = collection.find_one({'email': email})
    current_timestamp = datetime.now()
    
    if existing_entry:
        # Email exists, update the entry
        new_times = existing_entry['times'] + 1
        
        collection.update_one(
            {'email': email},
            {'$set': {'times': new_times, 'latest_timestamp': current_timestamp}}
        )
        print(f"Updated entry for email: {email}")
    else:
        # Email doesn't exist, create a new entry
        new_entry = {
            'email': email,
            'times': 1,
            'latest_timestamp': current_timestamp  # Set the default timestamp value
        }
        collection.insert_one(new_entry)
        print(f"Created new entry for email: {email}")

def get_public_ip():
    response = requests.get("https://api64.ipify.org?format=json")
    data = response.json()
    ip_address = data["ip"]
    # return "ec2-43-204-221-58.ap-south-1.compute.amazonaws.com"
    return "localhost"
    return ip_address

def get_free_port(email):
    """Find and return an available free port."""
    global database
    for port in range(start_port, end_port):
        if not database.check_port_in_use(port):
            return port
    return None

def start_new_target_app(free_port, email):
    """Start a new instance of target_app."""
    if free_port is None:
        return None, None
    # Set the timestamp in the DB dictionary when a new app is started
    timestamp = time.time()
    command = ["node", "Server/server.js", str(free_port)]
    process = subprocess.Popen(command, cwd="target_app")
    return process.pid, timestamp

"""
Cleans the state for this email if the time has expired.
If force is set as True, forcefully kill without thinking about timestamp.

* kills process
* cleans DB
* cleans PORTS_TO_EMAIL_MAP
"""
def clean_for_email(email, force=False):
    now = time.time()
    info = database.get_data_for_email(email)
    if not info:
        return
    try:
        port, pid, timestamp = info["port"], info["pid"], info.get("timestamp", 0)
        if force or (now - timestamp > kill_child_process_in_seconds):  # Check if the port was used for more than an hour
            print(f"Cleaning up port {port} for email {email}")
            try:
                os.kill(pid, 9)  # Send SIGKILL signal to terminate the process
                print(f"Process with PID {pid} killed")
            except Exception as e:
                print(f"Failed to kill process with PID {pid}: {e}")
            database.delete_email(email)
    except:
        pass


def cleanup_stale_ports():
    """Clean up ports for entries older than an hour in the DB."""
    for email in database.get_all_emails():
        clean_for_email(email)

def port_watcher():
    """Periodically check and clean up stale ports."""
    global database
    global stop_port_watcher
    while not stop_port_watcher:
        print("Triggering port watcher...")
        cleanup_stale_ports()
        time.sleep(sleep_watcher_for_seconds)  # Check every 60 seconds

def check_server_availability(port):
    """Check if the target_app server is responsive."""
    if port is None:
        return False
    try:
        response = requests.get(f"http://localhost:{port}/ping")
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


CODE_TO_DEBUG = "https://api.github.com/repos/abc/aaa/contents/Server/Routes/api.js"

def get_time():
    current_time = datetime.now(pytz.utc)
    timezone = pytz.timezone("Europe/London")  # Replace "Your_Timezone" with the desired timezone
    localized_time = current_time.astimezone(timezone)
    return localized_time.strftime("%Y-%m-%d %H:%M:%S %Z%z")

def generate_random_string(length):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(secrets.choice(characters) for _ in range(length))
    return random_string


async def websocket_handler(websocket, path):
    assert path == "/ws/app"
    async for message in websocket:
        message_json = json.loads(message)
        # print("Received:", message_json)
        if message_json["name"]=="FilterTracePointsRequest":
            # When the agent starts it sends this request
            # So we can save the websocket for this port and email
            port = int(message_json["applicationFilter"]["name"])
            email = database.get_email_for_port(port)
            if not email:
                print(f"Something wrong! email not found for port: {port}")
            if not database.set_websocket_for_email(email, websocket):
                print(f"Something wrong! email: {email} for port: {port} not recognized")

        if(message_json["name"] in ["TracePointSnapshotEvent"] ):
            live_message = {}
            live_message["timestamp"] = get_time()
            live_message["fileName"] = message_json["className"]
            live_message["methodName"] = message_json["methodName"]
            live_message["lineNo"] = message_json["lineNo"]
            # live_message["traceId"] = message_json["traceId"]
            # live_message["spanId"] = message_json["spanId"]
            if len(message_json["frames"])>0 and "variables" in message_json["frames"][0]:
                live_message["variables"] = message_json["frames"][0]["variables"]
            # Send the live_message to the connected client
            print("live_message",live_message)
            def send_live_message_to_server_js(port, live_message):
                url = f'http://{get_public_ip()}:{port}/addTracepointEvent'
                # print(url)
                headers = {'Content-Type': 'application/json'}
                data = {'port': port, 'live_message': live_message}
                response = requests.post(url, json=data, headers=headers)
                if response.status_code == 200:
                    print("Live message sent successfully.")
                else:
                    print("Failed to send live message.")
            # Call the function to send the live_message to the corresponding server.js
            send_live_message_to_server_js(port, live_message)


# start a WebSocket server on a thread
def run_websocket_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    start_server = websockets.serve(websocket_handler, 'localhost', 8094)
    print("WebSocket server running...")
    loop.run_until_complete(start_server)
    loop.run_forever()



async def _serialize_and_send(client_websocket, message_json):
    message_serialized = json.dumps(message_json)

    await client_websocket.send(message_serialized)

async def sendPutTracepoint(line_no, port):
    email = database.get_email_for_port(port)
    if not email:
        print(f"Something wrong! email not found for port: {port}")

    client_websocket = database.get_websocket_for_email(email)
    if not client_websocket:
        print(f"Unrecognized email: {email}")
        return
    tracePointId = generate_random_string(7)
    requestId = generate_random_string(7)
    message_json = {
        "name":"PutTracePointRequest",
        "type":"Request",
        "id":requestId,
        "client":"simulated_client_api",
        "tracePointId":tracePointId,
        "fileName":f"{CODE_TO_DEBUG}?ref=REF",
        "lineNo":line_no,
        "enableTracing":True,
        "conditionExpression":None,
    }
    await _serialize_and_send(client_websocket, message_json)
    database.update_tracepoint_map(email, line_no, tracePointId)

async def sendRemoveTracepoint(email, line_no):
    client_websocket = database.get_websocket_for_email(email)
    if not client_websocket:
        print(f"Unrecognized email: {email}")
        return

    tracePointId = database.get_tracePointId_for_email_lineno(email, line_no)
    if not tracePointId:
        print(f"Tracepoint not found for line number {line_no} and email {email}")
        return

    requestId = generate_random_string(7)
    message_json = {
        "name":"RemoveTracePointRequest",
        "type":"Request",
        "id":requestId,
        "client":"simulated_client_api",
        "tracePointId":tracePointId,
        "fileName":f"{CODE_TO_DEBUG}?ref=REF",
        "lineNo":line_no,
        "enableTracing":True,
        "conditionExpression":None,
    }
    await _serialize_and_send(client_websocket, message_json)
    database.delete_lineno_from_tracepointid_map_for_email(email, line_no)


@app.route('/tracepoint', methods=['POST'])
def receive_request():
    data = request.get_json()
    port = int(data.get('port'))
    lineNumber = data.get('lineNumber')+1
    print(f"Received request from port {port} for line number {lineNumber}")
    # Code to handle the received request 
    asyncio.run(sendPutTracepoint(lineNumber, port))
    response_data = {'message': 'Request received successfully!'}
    return jsonify(response_data), 200

@app.route('/removetracepoint', methods=['POST'])
def remove_tracepoint():
    data = request.get_json()
    port = data.get('port')
    lineNumber = data.get('lineNumber')+1
    print(f"Received request to remove tracepoint from port {port} for line number {lineNumber}")

     # Get the email associated with the port
    email = database.get_email_for_port(port)
    if email is not None:
        # Call the function to send the RemoveTracepoint request
        asyncio.run(sendRemoveTracepoint(email, lineNumber))
        response_data = {'message': f'RemoveTracepoint request sent for line number {lineNumber}'}
        return jsonify(response_data), 200
    else:
        response_data = {'message': 'Invalid port'}
        return jsonify(response_data), 400


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Handle the submitted email address
        email = request.form.get("email")
        if database.check_email_in_db(email):
            clean_for_email(email, force=True)
        # Spin a new server here
        free_port = get_free_port(email)
        database.set_port_for_email(email, free_port)
        if free_port:
            pid, timestamp = start_new_target_app(free_port, email)
        if pid:
            database.set_pid_for_email(email, pid)
            database.set_timestamp_for_email(email, timestamp)
            add_email_in_persistent_db(email)
        else:
            database.delete_email(email)
            return "No free ports available at the moment. Please try again later.", 500
        print(f"New target_app started on port {free_port} with process id {pid}")
        port = database.get_port_for_email(email)
        return render_template("sandbox_under_construction.html", email = email)
    else:
        # If the request is a GET, we render the HTML form asking for the email.
        return render_template("index.html")
    
@app.route("/sandbox", methods=["GET", "POST"])
def sandbox():
    email = request.args.get("email")
    port = database.get_port_for_email(email)
    if port and check_server_availability(port):
        return render_template("tic-tac-toe.html", port=port, server_url=f"http://{get_public_ip()}")
    else:
        return f"Failed to get data from localhost:{port}", 500
    
if __name__ == "__main__":
    # Start the port watcher as a separate thread
    watcher_thread = threading.Thread(target=port_watcher, daemon=True)
    watcher_thread.start()
    websocket_thread = threading.Thread(target=run_websocket_server)
    websocket_thread.start()
    try:
        app.run(debug=False, port=5001, host="0.0.0.0")
    except KeyboardInterrupt:
        # Set the stop_port_watcher flag to signal the port_watcher thread to stop
        stop_port_watcher=True
        # watcher_thread.join()  