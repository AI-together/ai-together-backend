import eventlet
eventlet.monkey_patch()  # eventlet 패치를 맨 위에 추가

import base64
import main
import logging
import signal
import sys
import threading
from dataclasses import dataclass
from typing import Dict
import os
import socketio
from flask import Flask, send_from_directory

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define client roles
class ClientRole:
    MONITOR = "monitor"
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

# Define EndMessage structure for "end" event
@dataclass
class EndMessage:
    end_frame: str
    end_img1: str
    end_img2: str

@dataclass
class CompositedEndMessage:
    composited_image: str  # Assuming AI sends back a single composited image

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

    def set_end_images(self, end_frame: str, end_img1: str, end_img2: str):
        # Optionally store end images if needed
        pass

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
    if role not in [ClientRole.MONITOR, ClientRole.LAPA]:
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


    image_ai = main.input(input_msg.__dict__, False)

    output(image_ai)
    '''
    ai_sid = hub.get_client_sid(ClientRole.AI)
    if ai_sid:
        sio.emit('input', input_msg.__dict__, to=ai_sid)
        logger.info("Sent 'input' event to AI client.")
    else:
        logger.warning("AI client is not connected.")
    '''
# 새로운 "output" 이벤트 핸들러 추가

def output(data):
    sid = 'ai'
    image_str = data  # 클라이언트에서 단순히 base64 문자열을 전송
    logger.info(image_str)
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
    '''
    # AI 클라이언트에 필터 업데이트 알림
    ai_sid = hub.get_client_sid(ClientRole.AI)
    if ai_sid:
        sio.emit('filter_updated', {'filter_number': filter_number}, to=ai_sid)
        logger.info(f"Sent 'filter_updated' event to AI client (SID {ai_sid}) with filter_number {filter_number}")
    else:
        logger.warning("AI client is not connected. Cannot send 'filter_updated' event.")
    '''
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
    '''
    # AI 클라이언트에 인원 수 업데이트 알림
    ai_sid = hub.get_client_sid(ClientRole.AI)
    if ai_sid:
        sio.emit('people_updated', {'people_count': people_count}, to=ai_sid)
        logger.info(f"Sent 'people_updated' event to AI client (SID {ai_sid}) with people_count {people_count}")
    else:
        logger.warning("AI client is not connected. Cannot send 'people_updated' event.")
    '''
    # 인원 수가 성공적으로 업데이트되었음을 클라이언트에 알림
    sio.emit('people_count_set', {'people_count': people_count}, to=sid)
    logger.info(f"People count set to {people_count} by SID {sid}")

# 새로운 "trigger_end" 이벤트 핸들러 추가
@sio.event
def trigger_end(sid, data):
    """
    This event can be emitted by a client (e.g., Monitor) to request the server to send
    the 'end' event to the AI client with three image strings.
    """
    logger.info(f"Received 'trigger_end' event from SID {sid}: {data}")

    # 역할 확인
    sender_role = None
    with hub.lock:
        for role, client_sid in hub.clients.items():
            if client_sid == sid:
                sender_role = role
                break

    # Define which roles are allowed to trigger the 'end' event
    if sender_role not in [ClientRole.MONITOR, 'admin', ClientRole.LAPA]:
        logger.warning(f"Unauthorized attempt to trigger 'end' by role '{sender_role}' (SID {sid})")
        sio.emit('error', {'message': 'Unauthorized to trigger end'}, to=sid)
        return

    # 데이터 검증
    if not isinstance(data, dict):
        logger.error("Invalid data format for 'trigger_end'. Expected a dictionary.")
        sio.emit('error', {'message': 'Invalid data format. Expected a dictionary with end images.'}, to=sid)
        return

    end_frame = data.get('end_frame')
    end_img1 = data.get('end_img1')
    end_img2 = data.get('end_img2')

    if not all(isinstance(img, str) for img in [end_frame, end_img1, end_img2]):
        logger.error("Invalid end image data format. All end images must be base64 strings.")
        sio.emit('error', {'message': 'Invalid end image data format. All end images must be base64 strings.'}, to=sid)
        return

    # Optionally, store the end images
    hub.set_end_images(end_frame, end_img1, end_img2)

    # Create EndMessage
    end_msg = EndMessage(
        end_frame=end_frame,
        end_img1=end_img1,
        end_img2=end_img2
    )
    end(end_msg.__dict__)
    # Send 'end' event to AI client
    ai_sid = hub.get_client_sid(ClientRole.AI)
    if ai_sid:
        sio.emit('end', end_msg.__dict__, to=ai_sid)
        logger.info(f"Sent 'end' event to AI client (SID {ai_sid}) with end images.")
    else:
        logger.warning("AI client is not connected. Cannot send 'end' event.")

    # Acknowledge the trigger to the sender
    sio.emit('end_triggered', {'message': 'End event triggered successfully.'}, to=sid)
    logger.info(f"'end' event triggered by SID {sid}")
'''
def save_base64_image(image_base64, output_dir, output_file):
    try:
        # 디렉토리가 없으면 생성
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Base64 디코딩
        image_data = base64.b64decode(image_base64 + '==')

        # 파일 저장 경로
        output_path = os.path.join(output_dir, output_file)

        # 파일로 저장
        with open(output_path, 'wb') as file:
            file.write(image_data)

        print(f"이미지가 {output_path}에 저장되었습니다.")
    except Exception as e:
        print(f"에러 발생: {e}")

'''

@sio.event
def result(sid, data):
    logger.info(f"Received 'result' event from SID {sid}")

    # 역할 확인
    sender_role = None
    with hub.lock:
        for role, client_sid in hub.clients.items():
            if client_sid == sid:
                sender_role = role
                break

    if not sender_role:
        logger.warning(f"'result' event from unregistered client: SID {sid}")
        sio.emit('error', {'message': 'Role not registered'}, to=sid)
        return

    if sender_role != ClientRole.MONITOR:
        logger.warning(f"Unauthorized 'result' event from role '{sender_role}' (SID {sid})")
        sio.emit('error', {'message': 'Unauthorized event'}, to=sid)
        return

    image_str = data  # 클라이언트에서 단순히 base64 문자열을 전송
    if not isinstance(image_str, str):
        logger.error("Invalid image data format.")
        sio.emit('error', {'message': 'Invalid image data'}, to=sid)
        return

    hub.set_input_image_data(image_str)

    input_msg = InputMessage(
        image=hub.input_image_data,
        filter_number=hub.filter_number,
        people_count=hub.people_count
    )


    main.input(input_msg.__dict__, True)

    '''
    output_directory = r"C:\/Users\kyle0\Desktop\/ai-together-backend_new\/res_img"
    output_filename = "last_image.png"

    save_base64_image(image['image'], output_directory, output_filename)
    '''

'''
# 새로운 "end" 이벤트 핸들러 추가 (수신 부분)
@sio.event
def end(sid, data):
    """
    This handler processes the 'end' event received from the AI client.
    It expects a composited image and forwards it to the Monitor client.
    """
    logger.info(f"Received 'end' event from SID {sid}: {data}")

    # 역할 확인
    sender_role = None
    with hub.lock:
        for role, client_sid in hub.clients.items():
            if client_sid == sid:
                sender_role = role
                break

    if not sender_role:
        logger.warning(f"'end' event from unregistered client: SID {sid}")
        sio.emit('error', {'message': 'Role not registered'}, to=sid)
        return

    if sender_role != ClientRole.AI:
        logger.warning(f"Unauthorized 'end' event from role '{sender_role}' (SID {sid})")
        sio.emit('error', {'message': 'Unauthorized event'}, to=sid)
        return

    # 데이터 검증
    if not isinstance(data, dict):
        logger.error("Invalid data format for 'end' event. Expected a dictionary.")
        sio.emit('error', {'message': 'Invalid data format for end event.'}, to=sid)
        return

    composited_image = data.get('composited_image')
    if not isinstance(composited_image, str):
        logger.error("Invalid composited image format. Must be a base64 string.")
        sio.emit('error', {'message': 'Invalid composited image format.'}, to=sid)
        return

    # Optionally, store the composited image
    # hub.set_composited_image(composited_image)

    # Forward the composited image to the Monitor client
    monitor_sid = hub.get_client_sid(ClientRole.MONITOR)
    if monitor_sid:
        composited_msg = {'composited_image': composited_image}
        sio.emit('end_composited', composited_msg, to=monitor_sid)
        logger.info("Sent 'end_composited' event to Monitor client.")
    else:
        logger.warning("Monitor client is not connected. Cannot send 'end_composited' event.")
'''

def end(sid, data):
    """
    This handler processes the 'end' event received from the AI client.
    It expects a composited image and forwards it to the Monitor client.
    """
    sid = 'ai'
    logger.info(f"Received 'end' event from SID {sid}: {data}")


    # 데이터 검증
    if not isinstance(data, dict):
        logger.error("Invalid data format for 'end' event. Expected a dictionary.")
        sio.emit('error', {'message': 'Invalid data format for end event.'}, to=sid)
        return

    composited_image = data.get('composited_image')
    if not isinstance(composited_image, str):
        logger.error("Invalid composited image format. Must be a base64 string.")
        sio.emit('error', {'message': 'Invalid composited image format.'}, to=sid)
        return

    # Optionally, store the composited image
    # hub.set_composited_image(composited_image)

    # Forward the composited image to the Monitor client
    monitor_sid = hub.get_client_sid(ClientRole.MONITOR)
    if monitor_sid:
        composited_msg = {'composited_image': composited_image}
        sio.emit('end_composited', composited_msg, to=monitor_sid)
        logger.info("Sent 'end_composited' event to Monitor client.")
    else:
        logger.warning("Monitor client is not connected. Cannot send 'end_composited' event.")

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
    import os
    import base64
    from flask import Flask, request, jsonify
    from PIL import Image
    from io import BytesIO

    app = Flask(__name__)

    # 이미지 업로드 경로 설정
    UPLOAD_FOLDER = 'uploads'
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    @app.route('/upload', methods=['POST'])
    def upload_image():
        try:
            # Base64 문자열 받기
            data = request.json.get('image_data')
            if not data:
                return jsonify({"error": "No image data provided"}), 400

            # Base64로 인코딩된 데이터를 디코딩하여 이미지로 변환
            img_data = base64.b64decode(data.split(',')[1])  # data URI 형식 처리 (prefix 제거)
            image = Image.open(BytesIO(img_data))

            # 이미지 파일로 저장
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'uploaded_image.png')
            image.save(file_path)

            # 이미지가 업로드된 URL 반환 (서버에서 이미지 제공)
            image_url = f"http://localhost:5000/{file_path}"
            return jsonify({"image_url": image_url}), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    if __name__ == '__main__':
        app.run(debug=True)


if __name__ == '__main__':
    # Handle graceful shutdown
    signal.signal(signal.SIGINT, shutdown_server)
    signal.signal(signal.SIGTERM, shutdown_server)

    logger.info("Starting server on 0.0.0.0:8888")

    run_server()
