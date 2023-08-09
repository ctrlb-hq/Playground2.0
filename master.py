from flask import Flask, render_template, request, redirect, jsonify
from flask_cors import CORS
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
import hashlib 
import secrets
import string

app = Flask(__name__)
CORS(app)

# Flag to signal the port_watcher thread to stop
stop_port_watcher = False
DB = {}
PORTS_USED = set()


def get_public_ip():
    response = requests.get("https://api64.ipify.org?format=json")
    data = response.json()
    ip_address = data["ip"]
    return ip_address

def get_free_port():
    """Find and return an available free port."""
    global PORTS_USED
    for port in range(9000, 10000):
        if port not in PORTS_USED:
            PORTS_USED.add(port)
            return port
    return None

def start_new_target_app():
    """Start a new instance of target_app."""
    free_port = get_free_port()
    if free_port is None:
        return None, None
    # Set the timestamp in the DB dictionary when a new app is started
    timestamp = time.time()
    command = ["node", "Server/server.js", str(free_port)]
    process = subprocess.Popen(command, cwd="target_app")
    print("Sleeping for 2 seconds...")
    time.sleep(2)
    return free_port, process.pid, timestamp

def cleanup_stale_ports():
    """Clean up ports for entries older than an hour in the DB."""
    now = time.time()
    for email, info in list(DB.items()):
        port, pid, timestamp = info["port"], info["pid"], info.get("timestamp", 0)
        if now - timestamp > 60:  # Check if the port was used for more than an hour
            print(f"Cleaning up port {port} for email {email}")
            try:
                os.kill(pid, 9)  # Send SIGKILL signal to terminate the process
                print(f"Process with PID {pid} killed")
            except Exception as e:
                print(f"Failed to kill process with PID {pid}: {e}")
            del DB[email]  # Remove the entry from the dictionary
            PORTS_USED.remove(port)  # Free up the port in the PORTS_USED set

def port_watcher(DB):
    """Periodically check and clean up stale ports."""
    global stop_port_watcher
    while not stop_port_watcher:
        print("Running port watcher...")
        if not DB:  # Check if DB is empty
            print("DB is empty")
        else:
            print(f"length = {len(DB.items())}")
        cleanup_stale_ports()
        time.sleep(60)  # Check every 60 seconds

def check_server_availability(port):
    """Check if the target_app server is responsive."""
    try:
        response = requests.get(f"http://localhost:{port}/ping")
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


CLIENT_WEBSOCKET = None
CODE_TO_DEBUG = "./target_app/Server/Routes/api.js"
OUTPUT_DEBUGEE = []
LIVE_SNAPSHOTS = []
FRONTEND_TRACEPOINTS = []
LINENO_TO_TRACEPOINTID_MAP = {}
REQUESTID_TO_LINENO_MAP = {}


def get_time():
    current_time = datetime.now(pytz.utc)
    timezone = pytz.timezone("Europe/London")  # Replace "Your_Timezone" with the desired timezone
    localized_time = current_time.astimezone(timezone)
    return localized_time.strftime("%Y-%m-%d %H:%M:%S %Z%z")

def generate_random_string(length):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(secrets.choice(characters) for _ in range(length))
    return random_string

def get_source_code(file_path):
    if file_path is None or file_path.endswith('.pyc'):
        return None
    try:
        with open(file_path, 'rb') as f:
            file_content = f.read()
            return file_content
    except IOError as e:
        print('Error reading file from file path: ' + file_path + ' err:', e)
    return None

def get_source_code_hash(file_path):
    source_code = get_source_code(file_path)
    if source_code is None:
        return None

    source_code = source_code.decode().replace('\r\n', '\n') \
        .replace('\r\x00\n\x00', '\n\x00') \
        .replace('\r', '\n').encode('UTF8')

    try:
        source_hash = hashlib.sha256(source_code).hexdigest()
        return source_hash
    except Exception as e:
        print('Unable to calculate hash of source code from file %s error: %s' % (file_path, e))

    return None

# start a WebSocket server on a thread
def run_websocket_server():
    global CLIENT_WEBSOCKET
    async def websocket_handler(websocket, path):
        global CLIENT_WEBSOCKET
        global LIVE_SNAPSHOTS
        global REQUESTID_TO_LINENO_MAP
        global FRONTEND_TRACEPOINTS
        assert path == "/ws/app"
        CLIENT_WEBSOCKET = websocket
        print("client webso", CLIENT_WEBSOCKET)
        try:
            async for message in websocket:
                message_json = json.loads(message)
                print("message_json1=", message_json)
                if(message_json["name"] in ["TracePointSnapshotEvent"] ):
                    live_message = {}
                    live_message["timestamp"] = get_time()
                    live_message["fileName"] = message_json["fileName"][:message_json["fileName"].index("?")]
                    live_message["methodName"] = message_json["methodName"]
                    live_message["lineNo"] = message_json["lineNo"]
                    live_message["traceId"] = message_json["traceId"]
                    live_message["spanId"] = message_json["spanId"]
                    if len(message_json["frames"])>0 and "variables" in message_json["frames"][0]:
                        live_message["variables"] = message_json["frames"][0]["variables"]
                    LIVE_SNAPSHOTS.append(json.dumps(live_message))
                if(message_json["name"] == "PutTracePointResponse"):
                    if(message_json["erroneous"]==False):
                        lineno = REQUESTID_TO_LINENO_MAP[message_json["requestId"]]
                        FRONTEND_TRACEPOINTS[lineno-1] = True
                        del REQUESTID_TO_LINENO_MAP[message_json["requestId"]]
                if(message_json["name"] == "RemoveTracePointResponse"):
                    if(message_json["erroneous"]==False):
                        lineno = REQUESTID_TO_LINENO_MAP[message_json["requestId"]]
                        FRONTEND_TRACEPOINTS[lineno-1] = False
                        del REQUESTID_TO_LINENO_MAP[message_json["requestId"]]
        except websockets.exceptions.ConnectionClosedOK:
            pass  # Connection closed gracefully
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            CLIENT_WEBSOCKET = None  # Reset the global variable on connection close
            # You can add a reconnection logic here
            retry_interval = 5  # Adjust the interval as needed
            while True:
                try:
                    print("Trying to reconnect...")
                    async with websockets.connect('ws://localhost:8094/ws/app') as new_websocket:
                        await websocket_handler(new_websocket, path)
                except Exception as e:
                    print(f"Reconnection failed. Retrying in {retry_interval} seconds.")
                    time.sleep(retry_interval)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    start_server = websockets.serve(websocket_handler, 'localhost', 8094)
    print("WebSocket server running...")
    loop.run_until_complete(start_server)
    loop.run_forever()



async def _serialize_and_send(message_json):
    message_serialized = json.dumps(message_json)

    await CLIENT_WEBSOCKET.send(message_serialized)

async def sendPutTracepoint(line_no):
    global LINENO_TO_TRACEPOINTID_MAP
    global CLIENT_WEBSOCKET
    global REQUESTID_TO_LINENO_MAP
    if CLIENT_WEBSOCKET is None:
        print("WebSocket connection is not yet established. Skipping sendPutTracepoint.")
        return
    print("is it run")
    file_hash = get_source_code_hash(CODE_TO_DEBUG)
    tracePointId = generate_random_string(7)
    requestId = generate_random_string(7)
    message_json = {
        "name":"PutTracePointRequest",
        "type":"Request",
        "id":requestId,
        "client":"simulated_client_api",
        "tracePointId":tracePointId,
        "fileName":f"{CODE_TO_DEBUG}?ref=REF",
        "fileHash":file_hash,
        "lineNo":line_no,
        "enableTracing":True,
        "conditionExpression":None,
    }
    await _serialize_and_send(message_json)
    LINENO_TO_TRACEPOINTID_MAP[line_no] = tracePointId
    REQUESTID_TO_LINENO_MAP[requestId] = line_no

async def sendRemoveTracepoint(line_no):
    global FRONTEND_TRACEPOINTS
    global REQUESTID_TO_LINENO_MAP
    file_hash = get_source_code_hash(CODE_TO_DEBUG)
    tracePointId = LINENO_TO_TRACEPOINTID_MAP[line_no]
    requestId = generate_random_string(7)
    message_json = {
        "name":"RemoveTracePointRequest",
        "type":"Request",
        "id":requestId,
        "client":"simulated_client_api",
        "tracePointId":tracePointId,
        "fileName":f"{CODE_TO_DEBUG}?ref=REF",
        "fileHash":file_hash,
        "lineNo":line_no,
        "enableTracing":True,
        "conditionExpression":None,
    }
    await _serialize_and_send(message_json)
    REQUESTID_TO_LINENO_MAP[requestId] = line_no


@app.route('/tracepoint', methods=['POST'])
def receive_request():
    data = request.get_json()
    port = data.get('port')
    lineNumber = data.get('lineNumber')
    print(f"Received request from port {port} for line number {lineNumber}")
    # Code to handle the received request 
    asyncio.run(sendPutTracepoint(lineNumber))
    response_data = {'message': 'Request received successfully!'}
    return jsonify(response_data), 200

# @app.route('/removetracepoint', methods=['POST'])
# def remove_tracepoint():
#     data = request.get_json()
#     port = data.get('port')
#     lineNumber = data.get('lineNumber')
#     print(f"Received request to remove tracepoint from port {port} for line number {lineNumber}")

#     # Call the function to send the RemoveTracepoint request
#     asyncio.run(sendRemoveTracepoint(port, lineNumber))

#     response_data = {'message': 'Request received successfully!'}
#     return jsonify(response_data), 200


@app.route("/", methods=["GET", "POST"])
def index():
    global DB
    if request.method == "POST":
        # Handle the submitted email address
        email = request.form.get("email")
        if email not in DB:
            # Spin a new server here
            port, pid, timestamp = start_new_target_app()
            if port and pid:
                DB[email] = {
                    "port": port,
                    "pid": pid,
                    "timestamp": timestamp
                }
            else:
                return "No free ports available at the moment. Please try again later.", 500
            print(f"New target_app started on port {port} with process id {pid}")
        else:
            # If the email already exists, update the "timestamp"
            DB[email]["timestamp"] = time.time()
            print(f"Timestamp updated for email {email}")
        port = DB[email]["port"]
        if not DB:  # Check if DB is empty
            print("DB is empty index")
        else:
            print(f"length index = {len(DB.items())}")
        # Check if the target_app server is responsive
        if check_server_availability(port):
            return render_template("tic-tac-toe.html", port=port, server_url=f"http://{get_public_ip()}")
        else:
            # If the server is not responsive, redirect to index.html
            print("error")
            return f"Failed to get data from localhost:{port}", 500
    else:
        # If the request is a GET, we render the HTML form asking for the email.
        return render_template("index.html")
    
if __name__ == "__main__":
    # Start the port watcher as a separate thread
    watcher_thread = threading.Thread(target=port_watcher, args=(DB,), daemon=True)
    watcher_thread.start()
    # websocket_thread = threading.Thread(target=run_websocket_server, daemon=True)
    # websocket_thread.start()
    try:
        app.run(debug=True, port=5001, host="0.0.0.0")
    except KeyboardInterrupt:
        # Set the stop_port_watcher flag to signal the port_watcher thread to stop
        stop_port_watcher=True
        # watcher_thread.join()  