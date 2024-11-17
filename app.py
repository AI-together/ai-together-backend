import eventlet
eventlet.monkey_patch()  # eventlet 패치를 맨 위에 추가

import logging
import signal
import sys
import threading
from dataclasses import dataclass
from typing import Dict

import socketio
from flask import Flask, send_from_directory

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define client roles
class ClientRole:
    MONITOR = "monitor"
    AI = "ai"
    LAPA = "lapa"

# Define message structures
@dataclass
class InputMessage:
    image: str
    filter_number: int
    people_count: int

@dataclass
class OutputMessage:
    image: str

# Hub to manage clients and shared state
class Hub:
    def __init__(self):
        self.clients: Dict[str, str] = {}  # role -> sid
        self.filter_number: int = 0
        self.people_count: int = 1
        self.input_image_data: str = ""
        self.output_image_data: str = ""
        self.lock = threading.Lock()

    def register_client(self, role: str, sid: str, sio: socketio.Server):
        with self.lock:
            if role in self.clients:
                # Disconnect the old client
                old_sid = self.clients[role]
                sio.disconnect(old_sid)
                logger.info(f"Existing client for role '{role}' disconnected: SID {old_sid}")
            self.clients[role] = sid
            logger.info(f"Client registered: Role '{role}', SID {sid}")

    def unregister_client(self, sid: str):
        with self.lock:
            for role, client_sid in list(self.clients.items()):
                if client_sid == sid:
                    del self.clients[role]
                    logger.info(f"Client disconnected: Role '{role}', SID {sid}")
                    break

    def get_client_sid(self, role: str) -> str:
        with self.lock:
            return self.clients.get(role, "")

    def set_filter_number(self, filter_number: int):
        with self.lock:
            self.filter_number = filter_number
            logger.info(f"Filter number updated to: {filter_number}")

    def set_people_count(self, people_count: int):
        with self.lock:
            self.people_count = people_count
            logger.info(f"People count updated to: {people_count}")

    def set_input_image_data(self, image_data: str):
        with self.lock:
            self.input_image_data = image_data
            logger.info("Input image data updated.")

    def set_output_image_data(self, image_data: str):
        with self.lock:
            self.output_image_data = image_data
            logger.info("Output image data updated.")

# Initialize Flask and Socket.IO
app = Flask(__name__, static_folder='public')
sio = socketio.Server(
    async_mode='eventlet',
    cors_allowed_origins='*'  # 모든 출처 허용 (보안 필요 시 특정 도메인으로 제한)
)
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)

# Initialize Hub
hub = Hub()

# Socket.IO event handlers
@sio.event
def connect(sid, environ):
    logger.info(f"New connection: SID {sid}")

@sio.event
def disconnect(sid):
    hub.unregister_client(sid)
    logger.info(f"Disconnected: SID {sid}")

@sio.event
def register(sid, data):
    role = data.get('role')
    if role not in [ClientRole.MONITOR, ClientRole.AI, ClientRole.LAPA]:
        logger.warning(f"Invalid role registration attempt: '{role}' by SID {sid}")
        sio.emit('error', {'message': 'Invalid role'}, to=sid)
        return

    hub.register_client(role, sid, sio)
    sio.emit('registered', {'role': role}, to=sid)
    logger.info(f"Client registered with role '{role}': SID {sid}")

# 새로운 "image" 이벤트 핸들러 추가
@sio.event
def image(sid, data):
    logger.info(f"Received 'image' event from SID {sid}")

    # 역할 확인
    sender_role = None
    with hub.lock:
        for role, client_sid in hub.clients.items():
            if client_sid == sid:
                sender_role = role
                break

    if not sender_role:
        logger.warning(f"'image' event from unregistered client: SID {sid}")
        sio.emit('error', {'message': 'Role not registered'}, to=sid)
        return

    if sender_role != ClientRole.MONITOR:
        logger.warning(f"Unauthorized 'image' event from role '{sender_role}' (SID {sid})")
        sio.emit('error', {'message': 'Unauthorized event'}, to=sid)
        return

    image_str = data  # 클라이언트에서 단순히 base64 문자열을 전송
    if not isinstance(image_str, str):
        logger.error("Invalid image data format.")
        sio.emit('error', {'message': 'Invalid image data'}, to=sid)
        return

    hub.set_input_image_data(image_str)

    # 현재 filter_number 로그
    logger.info(f"Current filter_number before sending to AI: {hub.filter_number}")

    input_msg = InputMessage(
        image=hub.input_image_data,
        filter_number=hub.filter_number,
        people_count=hub.people_count
    )
    ai_sid = hub.get_client_sid(ClientRole.AI)
    if ai_sid:
        sio.emit('input', input_msg.__dict__, to=ai_sid)
        logger.info("Sent 'input' event to AI client.")
    else:
        logger.warning("AI client is not connected.")

@sio.event
def output(sid, data):
    # 추가: AI 클라이언트로부터의 "output" 이벤트 핸들러
    logger.info(f"Received 'output' event from SID {sid}: base64data (type: {type(data)})")

    # 역할 확인
    sender_role = None
    with hub.lock:
        for role, client_sid in hub.clients.items():
            if client_sid == sid:
                sender_role = role
                break

    if not sender_role:
        logger.warning(f"'output' event from unregistered client: SID {sid}")
        sio.emit('error', {'message': 'Role not registered'}, to=sid)
        return

    if sender_role != ClientRole.AI:
        logger.warning(f"Unauthorized 'output' event from role '{sender_role}' (SID {sid})")
        sio.emit('error', {'message': 'Unauthorized event'}, to=sid)
        return

    image_str = data  # 클라이언트에서 단순히 base64 문자열을 전송
    if not isinstance(image_str, str):
        logger.error("Invalid output image data format.")
        sio.emit('error', {'message': 'Invalid output data'}, to=sid)
        return

    hub.set_output_image_data(image_str)
    monitor_sid = hub.get_client_sid(ClientRole.MONITOR)
    if monitor_sid:
        output_msg = OutputMessage(image=image_str)
        sio.emit('image', output_msg.__dict__, to=monitor_sid)
        logger.info("Sent 'image' event to Monitor client.")
    else:
        logger.warning("Monitor client is not connected.")

# 새로운 "filter" 이벤트 핸들러 수정 (ClientRole.LAPA 추가)
@sio.event
def filter(sid, data):
    logger.info(f"Received 'filter' event from SID {sid}: {data}")

    # 역할 확인
    sender_role = None
    with hub.lock:
        for role, client_sid in hub.clients.items():
            if client_sid == sid:
                sender_role = role
                break

    if sender_role not in [ClientRole.MONITOR, 'admin', ClientRole.LAPA]:
        logger.warning(f"Unauthorized attempt to set filter_number by role '{sender_role}' (SID {sid})")
        sio.emit('error', {'message': 'Unauthorized to set filter_number'}, to=sid)
        return

    # 데이터 검증
    if not isinstance(data, int):
        logger.error("Invalid filter_number format. Must be an integer.")
        sio.emit('error', {'message': 'Invalid filter_number format. Must be an integer.'}, to=sid)
        return

    filter_number = data  # 정수형 데이터 직접 할당

    # 필터 번호 업데이트
    hub.set_filter_number(filter_number)

    # AI 클라이언트에 필터 업데이트 알림
    ai_sid = hub.get_client_sid(ClientRole.AI)
    if ai_sid:
        sio.emit('filter_updated', {'filter_number': filter_number}, to=ai_sid)
        logger.info(f"Sent 'filter_updated' event to AI client (SID {ai_sid}) with filter_number {filter_number}")
    else:
        logger.warning("AI client is not connected. Cannot send 'filter_updated' event.")

    # 필터 번호가 성공적으로 업데이트되었음을 클라이언트에 알림
    sio.emit('filter_number_set', {'filter_number': filter_number}, to=sid)
    logger.info(f"Filter number set to {filter_number} by SID {sid}")

# 새로운 "people" 이벤트 핸들러 추가
@sio.event
def people(sid, data):
    logger.info(f"Received 'people' event from SID {sid}: {data}")

    # 역할 확인
    sender_role = None
    with hub.lock:
        for role, client_sid in hub.clients.items():
            if client_sid == sid:
                sender_role = role
                break

    if sender_role != ClientRole.LAPA:
        logger.warning(f"Unauthorized attempt to set people_count by role '{sender_role}' (SID {sid})")
        sio.emit('error', {'message': 'Unauthorized to set people_count'}, to=sid)
        return

    # 데이터 검증
    if not isinstance(data, int) or data < 1:
        logger.error("Invalid people_count format. Must be a positive integer.")
        sio.emit('error', {'message': 'Invalid people_count format. Must be a positive integer.'}, to=sid)
        return

    people_count = data  # 정수형 데이터 직접 할당

    # 인원 수 업데이트
    hub.set_people_count(people_count)

    # AI 클라이언트에 인원 수 업데이트 알림
    ai_sid = hub.get_client_sid(ClientRole.AI)
    if ai_sid:
        sio.emit('people_updated', {'people_count': people_count}, to=ai_sid)
        logger.info(f"Sent 'people_updated' event to AI client (SID {ai_sid}) with people_count {people_count}")
    else:
        logger.warning("AI client is not connected. Cannot send 'people_updated' event.")

    # 인원 수가 성공적으로 업데이트되었음을 클라이언트에 알림
    sio.emit('people_count_set', {'people_count': people_count}, to=sid)
    logger.info(f"People count set to {people_count} by SID {sid}")

# Serve static files from the "public" directory
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)

def run_server():
    # Run the server with eventlet
    eventlet.wsgi.server(eventlet.listen(('0.0.0.0', 8888)), app)

def shutdown_server(signum, frame):
    logger.info("Shutting down server...")
    sys.exit(0)

if __name__ == '__main__':
    # Handle graceful shutdown
    signal.signal(signal.SIGINT, shutdown_server)
    signal.signal(signal.SIGTERM, shutdown_server)

    logger.info("Starting server on 0.0.0.0:8888")
    run_server()
