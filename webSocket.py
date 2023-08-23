import threading
import requests
import websockets
import asyncio
import json
from datetime import datetime
import pytz
import secrets
import string
from datetime import datetime


CODE_TO_DEBUG = "https://api.github.com/repos/abc/aaa/contents/Server/Routes/api.js"
database = None 
get_public_ip= None

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

def websocket(database_obj, ip_add):
    global database
    global get_public_ip
    database = database_obj
    get_public_ip=ip_add
    websocket_thread = threading.Thread(target=run_websocket_server)
    websocket_thread.start()
