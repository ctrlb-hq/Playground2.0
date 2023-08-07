from flask import Flask, render_template, request, redirect, jsonify
from flask_cors import CORS
import subprocess
import time
import os
import threading
import requests

app = Flask(__name__)
CORS(app)

DB = {}
PORTS_USED = set()
# Flag to signal the port_watcher thread to stop
stop_port_watcher = False

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
        response = requests.get(f"http://localhost:{port}")
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


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
            return render_template("tic-tac-toe.html", port=port)
        else:
            # If the server is not responsive, redirect to index.html
            print("error")
            return f"Failed to get data from localhost:{port}", 500
    else:
        # If the request is a GET, we render the HTML form asking for the email.
        return render_template("index.html")

@app.route('/tracepoint', methods=['POST'])
def receive_request():
    data = request.get_json()
    port = data.get('port')
    lineNumber = data.get('lineNumber')
    print(f"Received request from port {port} for line number {lineNumber}")
    # Your code to handle the received request goes here
    # ...

    response_data = {'message': 'Request received successfully!'}
    return jsonify(response_data), 200

if __name__ == "__main__":
    # Start the port watcher as a separate thread
    watcher_thread = threading.Thread(target=port_watcher, args=(DB,), daemon=True)
    watcher_thread.start()
    try:
        app.run(debug=True, port=5001, host="0.0.0.0")
    except KeyboardInterrupt:
        # Set the stop_port_watcher flag to signal the port_watcher thread to stop
        stop_port_watcher=True
        # watcher_thread.join()  