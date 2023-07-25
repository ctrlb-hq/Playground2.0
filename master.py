from flask import Flask, render_template, request, Response, send_file
import multiprocessing
# import concurrent.futures
import subprocess
import time
import platform
import requests
import os
import threading

# multiprocessing.freeze_support()  # Add freeze_support() for Windows compatibility


app = Flask(__name__)
# cwd = os.getcwd()
"""
Stores:
{
    email: {
        port: <port of target app>,
        pid: <process id of target app>,
    }
}
"""
# Use Manager to create a shared DB dictionary
# manager = multiprocessing.Manager()
DB = {}
PORTS_USED = set()  # to maintain what all ports have been used


def get_free_port():
    global PORTS_USED
    for port in range(9000, 10000):
        if port not in PORTS_USED:
            PORTS_USED.add(port)
            return port
    return None


"""
    Starts a new instance of target_app
    Returns: port, pid if everything is good else returns None, None
"""


def start_new_target_app():
    # os.chdir(cwd)
    free_port = get_free_port()
    if free_port == None:
        return None, None
    # Set the timestamp in the DB dictionary when a new app is started
    timestamp = time.time()
    cmd = f"cd target_app && node Server/server.js {free_port}"
    command = ["node", "Server/server.js", str(free_port)]

    process = subprocess.Popen(command, cwd="target_app")
    print("Sleeping for 2 seconds...")
    time.sleep(2)
    return free_port, process.pid, timestamp # Add a timestamp to the return value

def port_watcher(DB):
    while True:
        print("Running port watcher...")
        now = time.time()
        if not DB:  # Check if DB is empty
            print("DB is empty")
        else:
            print(f"length = {len(DB.items())}")
        # Iterate over a copy of the dictionary to avoid concurrent modification issues
        for email, info in list(DB.items()):
            port, pid, timestamp = info["port"], info["pid"], info.get("timestamp", 0)
            print(f"timestamp left {now - timestamp}")
            if now - timestamp > 60:  # Check if the port was used for more than an hour
                print(f"Cleaning up port {port} for email {email}")
                try:
                    os.kill(pid, 9)  # Send SIGKILL signal to terminate the process
                    print(f"Process with PID {pid} killed")
                except Exception as e:
                    print(f"Failed to kill process with PID {pid}: {e}")
                del DB[email]  # Remove the entry from the dictionary
                PORTS_USED.remove(port)  # Free up the port in the PORTS_USED set
        time.sleep(60)  # Check every 60 minutes

@app.route("/", methods=["GET", "POST"])
def index():
    global DB
    if request.method == "POST":
        # Here you can handle the submitted email address
        email = request.form.get("email")
        if email not in DB:
            # Spin a new server here
            port, pid, timestamp = start_new_target_app()
            if port and pid:
                DB[email] = {
                    "port": port,
                    "pid": pid,
                    "timestamp":timestamp
                }
            print(
                f"New target_app started on port {port} with process id {pid}")
        port = DB[email]["port"]
        if not DB:  # Check if DB is empty
            print("DB is empty index")
        else:
            print(f"length index= {len(DB.items())}")
        response = requests.get(f"http://localhost:{port}")
        if response.status_code == 200:
            return render_template("tic-tac-toe.html", port=port)
        else:
            print("error")
            return f"Failed to get data from localhost:{port}", 500
    else:
        # If the request is a GET, we render the HTML form asking for the email.
        return render_template("index.html")


if __name__ == "__main__":
    # Start the port watcher as a separate thread
    watcher_thread = threading.Thread(target=port_watcher, args=(DB,))
    watcher_thread.start()
    app.run(debug=True, port=5001, host="0.0.0.0")