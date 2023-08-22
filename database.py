import threading

class Database:
    def __init__(self):
        self.db_lock = threading.Lock()
        self.ports_to_email_map = {} # {port:email}
        self.db = {}
        #   {
        #   email:   {
        #       "port": port,
        #       "pid": pid,
        #       "timestamp": timestamp,
        #       "websocket": websocket,
        #       "tracepoint_map": {
        #             line_no: tracePointId,
        #         }
        #       }
        #   }
        
    def get_data_for_email(self, email):
        with self.db_lock:
            return self.db.get(email, None)
        
    def get_all_emails(self):
        with self.db_lock:
            emails = []
            for email, _ in list(self.db.items()):
                emails.append(email)
            return emails
        
    def delete_email(self, email):
        with self.db_lock:
            if email not in self.db:
                return
            port = self.db[email].get("port",None)
            del self.db[email]
            if port and int(port) in self.ports_to_email_map:
                del self.ports_to_email_map[int(port)]
    
    def set_websocket_for_email(self, email, websocket):
        with self.db_lock:
            if email not in self.db:
                return False
            self.db[email]["websocket"] = websocket
            return True
        
    def check_email_in_db(self, email):
        with self.db_lock:
            return email in self.db
        
    def get_websocket_for_email(self, email):
        status = self.check_email_in_db(email)
        if not status:
            return
        with self.db_lock:
            return self.db[email]["websocket"]
        
    def initialize_tracepointmap_if_not_exists(self, email):
        status = self.check_email_in_db(email)
        if not status:
            return
        with self.db_lock:
           if "tracepoint_map" not in self.db[email]:
                self.db[email]["tracepoint_map"] = {} 

    def update_tracepoint_map(self, email, line_no, tracePointId):
        status = self.check_email_in_db(email)
        if not status:
            return
        self.initialize_tracepointmap_if_not_exists(email)
        with self.db_lock:
            self.db[email]["tracepoint_map"][line_no] = tracePointId

    def get_tracePointId_for_email_lineno(self, email, line_no):
        if not self.check_email_in_db(email):
            return
        with self.db_lock:
            tracepointid_map = self.db[email].get("tracepoint_map",{})
            return tracepointid_map.get(line_no, None)
        
    def delete_lineno_from_tracepointid_map_for_email(self, email, line_no):
        if not self.check_email_in_db(email):
            return
        with self.db_lock:
            if "tracepoint_map" in self.db[email] and line_no in self.db[email]["tracepoint_map"]:
                del self.db[email]["tracepoint_map"][line_no]

    def set_port_for_email(self, email, port):
        if not self.check_email_in_db(email):
            with self.db_lock:
                self.db[email] = {}
        with self.db_lock:
            self.db[email]["port"] = int(port)
            self.ports_to_email_map[int(port)] = email

    def set_pid_for_email(self, email, pid):
        if not self.check_email_in_db(email):
            return
        with self.db_lock:
            self.db[email]["pid"] = pid

    def set_timestamp_for_email(self, email, timestamp):
        if not self.check_email_in_db(email):
            return
        with self.db_lock:
            self.db[email]["timestamp"] = timestamp

    def get_port_for_email(self, email):
        if not self.check_email_in_db(email):
            return
        with self.db_lock:
            return self.db[email].get("port",None)
        
    def check_port_in_use(self, port):
        with self.db_lock:
            return int(port) in self.ports_to_email_map
        
    def get_email_for_port(self, port):
        with self.db_lock:
            return self.ports_to_email_map.get(int(port), None)