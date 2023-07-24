from flask import Flask, render_template, request, Response, send_file
import multiprocessing
import subprocess
import os
import time
import requests

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
    cmd = f"cd target_app && node Server/server.js {free_port}"
    command = ["node", "Server/server.js", str(free_port)]

    process = subprocess.Popen(command, cwd="target_app")
    print("Sleeping for 2 seconds...")
    time.sleep(2)
    return free_port, process.pid


@app.route("/", methods=["GET", "POST"])
def index():
    global DB
    if request.method == "POST":
        # Here you can handle the submitted email address
        email = request.form.get("email")
        if email not in DB:
            # Spin a new server here
            port, pid = start_new_target_app()
            if port and pid:
                DB[email] = {
                    "port": port,
                    "pid": pid
                }
            print(
                f"New target_app started on port {port} with process id {pid}")
        port = DB[email]["port"]
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
    app.run(debug=True, port=5001, host="0.0.0.0")
