import threading
import time

def port_watcher(database):
    """Periodically check and clean up stale ports."""
    while True:
        print("Triggering port watcher...")
        cleanup_stale_ports(database)
        time.sleep(60)  # Check every 60 seconds


def clean_for_email(email, force=False):
    now = time.time()
    info = database.get_data_for_email(email)
    if not info:
        return
    try:
        port, pid, timestamp = info["port"], info["pid"], info.get("timestamp", 0)
        if force or (now - timestamp > 600):  # Check if the port was used for more than an hour
            print(f"Cleaning up port {port} for email {email}")
            try:
                os.kill(pid, 9)  # Send SIGKILL signal to terminate the process
                print(f"Process with PID {pid} killed")
            except Exception as e:
                print(f"Failed to kill process with PID {pid}: {e}")
            database.delete_email(email)
    except:
        pass

def cleanup_stale_ports(database):
    """Clean up ports for entries older than an hour in the DB."""
    for email in database.get_all_emails():
        clean_for_email(email, database)

def start_port_watcher(database):
    watcher_thread = threading.Thread(target=port_watcher, args=(database,), daemon=True)
    watcher_thread.start()