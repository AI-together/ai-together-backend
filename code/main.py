import qrcode
import socketio
import cv2
import mediapipe as mp
import numpy as np
import math
import picture
import base64
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
import os
import temp
import app

# Mediapipe Face Mesh 초기화
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=3,
    refine_landmarks=True,
    min_detection_confidence=0.2,
    min_tracking_confidence=0.2
)

# 쓰레드 풀
executor = ThreadPoolExecutor(max_workers=4)  # 이미지 처리를 위한 스레드 풀


# 얼굴 각도 계산 함수
def calculate_face_angle(face_landmarks, image_width, image_height):
    try:
        left_eye = [
            (face_landmarks.landmark[33].x + face_landmarks.landmark[133].x) / 2,
            (face_landmarks.landmark[33].y + face_landmarks.landmark[133].y) / 2
        ]
        right_eye = [
            (face_landmarks.landmark[362].x + face_landmarks.landmark[263].x) / 2,
            (face_landmarks.landmark[362].y + face_landmarks.landmark[263].y) / 2
        ]

        dx = (right_eye[0] - left_eye[0]) * image_width
        dy = (right_eye[1] - left_eye[1]) * image_height
        eye_angle = math.degrees(math.atan2(dy, dx))
        return max(-45, min(45, eye_angle))
    except Exception as e:
        app.logger.error(f"Error calculating face angle: {e}")
        return 0


# 얼굴 메시 처리 및 필터 적용 함수
def apply_face_mesh_sync(image, face_mesh, filter_image_path):
    image_height, image_width, _ = image.shape
    results = face_mesh.process(image)

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            angle = calculate_face_angle(face_landmarks, image_width, image_height)
            x = int(face_landmarks.landmark[1].x * image_width)
            y = int(face_landmarks.landmark[1].y * image_height)
            x1 = face_landmarks.landmark[152].x * image_width
            y1 = face_landmarks.landmark[152].y * image_height
            x2 = face_landmarks.landmark[10].x * image_width
            y2 = face_landmarks.landmark[10].y * image_height
            distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            filter_height = int(distance)
            filter_width = int(filter_height * 0.5)

            image = picture.take_pictures_start(
                filter_image_path, image, x, y,
                filter_width * 2, filter_height * 2,
                int(angle)
            )
    return image



def apply_face_mesh(image, face_mesh, filter_image_path):
    # 비동기 처리를 제거하고 동기적으로 바로 실행
    return apply_face_mesh_sync(image, face_mesh, filter_image_path)

'''
# 소켓 이벤트 핸들러
@sio.event
async def connect():
    print(12)
    logger.info("Connected to the server.")
    await sio.emit('register', {'role': 'ai'})


@sio.event
async def disconnect():
    logger.warning("Disconnected from the server.")
'''
'''
@sio.on('end')
async def in_image(data):
    try:
        end_frame = base64.b64decode(data['end_frame'] + '==')
        end_img1 = base64.b64decode(data['end_img1'] + '==')
        end_img2 = base64.b64decode(data['end_img2'] + '==')
        temp.img_connect(end_frame, end_img1, end_img2)

        image = cv2.imread('img/end.jpg')
        _, buffer = cv2.imencode(".jpg", image)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')

        await sio.emit('end', jpg_as_text)
        logger.info("Processed end image sent successfully.")

    except Exception as e:
        logger.error(f"Error during end image processing: {e}")
'''

def end(data):
    try:
        end_frame = base64.b64decode(data['end_frame'] + '==')
        end_img1 = base64.b64decode(data['end_img1'] + '==')
        end_img2 = base64.b64decode(data['end_img2'] + '==')
        temp.img_connect(end_frame, end_img1, end_img2)

        image = cv2.imread('img/end.jpg')
        _, buffer = cv2.imencode(".jpg", image)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')

        app.end(jpg_as_text)

    except Exception as e:
        app.logger.error(f"Error during end image processing: {e}")

'''
@sio.on('input')
async def receive_image(data):
    print(3333)
    try:
        img_data = base64.b64decode(data['image'] + '==')
        np_arr = np.frombuffer(img_data, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        filter_number = data.get('filter_number', 0)
        logger.info(f"Received filter number: {filter_number}")

        FILTER_DIRECTORY = r'C:\/Users\kyle0\Desktop\/trick-or-picture-main\/trick-or-picture-main\img'  # 필터 이미지 디렉토리

        filter_image = os.path.join(FILTER_DIRECTORY, f"{filter_number}.png")  # 경로 안전하게 결합
        print(f"Trying to find filter image at: {filter_image}")

        if os.path.isfile(filter_image):
            print("OK")
            filter_image_path = filter_image
        else:
            print(f"File does not exist: {filter_image}")
            logger.error("Failed to decode image")

        # BGR에서 RGB로 변환
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image.flags.writeable = True

        # 비동기로 이미지 처리
        processed_image = await apply_face_mesh_async(image, face_mesh, filter_image_path)

        # RGB에서 BGR로 변환
        processed_image = cv2.cvtColor(processed_image, cv2.COLOR_RGB2BGR)

        # 필터링된 이미지를 Base64로 인코딩
        _, buffer = cv2.imencode('.jpg', processed_image)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')

        await sio.emit('output', jpg_as_text)
        logger.info("Processed image sent successfully.")

    except Exception as e:
        logger.error(f"Error during image processing: {e}")
'''

def convert_image_to_qr(image_path, output_path):
    if not os.path.exists(image_path):
        print(f"이미지 파일이 존재하지 않습니다: {image_path}")
        return

    try:
        # 이미지 파일 읽기 및 Base64 인코딩
        with open(image_path, "rb") as img_file:
            image_data = base64.b64encode(img_file.read()).decode('utf-8')

        # QR 코드 생성
        qr = qrcode.QRCode(
            version=1,  # QR 코드 크기 조정
            error_correction=qrcode.constants.ERROR_CORRECT_L,  # 오류 보정 수준
            box_size=10,  # 박스 크기
            border=4,  # 여백 크기
        )
        qr.add_data(image_data)
        qr.make(fit=True)

        # QR 코드 이미지 생성 및 저장
        qr_image = qr.make_image(fill_color="black", back_color="white")
        qr_image.save(output_path)
        print(f"QR 코드가 생성되었습니다: {output_path}")

    except Exception as e:
        print(f"오류 발생: {e}")

def input(data, temp):
    try:
        img_data = base64.b64decode(data['image'] + '==')
        np_arr = np.frombuffer(img_data, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        filter_number = data.get('filter_number', 0)
        app.logger.info(f"Received filter number: {filter_number}")

        FILTER_DIRECTORY = r'C:\Users\kyle0\Desktop\trick-or-picture-main\trick-or-picture-main\img'  # 필터 이미지 디렉토리

        filter_image = os.path.join(FILTER_DIRECTORY, f"{filter_number}.png")  # 경로 안전하게 결합
        print(f"Trying to find filter image at: {filter_image}")

        if os.path.isfile(filter_image):
            print("OK")
            filter_image_path = filter_image
        else:
            print(f"File does not exist: {filter_image}")
            app.logger.error("Failed to decode image")

        # BGR에서 RGB로 변환
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image.flags.writeable = True

        # 비동기로 이미지 처리
        processed_image = apply_face_mesh(image, face_mesh, filter_image_path)

        # RGB에서 BGR로 변환
        processed_image = cv2.cvtColor(processed_image, cv2.COLOR_RGB2BGR)

        if temp:
            app.logger.info("save image to res_img")
            cv2.imwrite(r'../res_img/res.png', processed_image)
            #convert_image_to_qr("../res_img/res.png", "../qrcode/qr.png")


        # 필터링된 이미지를 Base64로 인코딩
        _, buffer = cv2.imencode('.jpg', processed_image)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')

        app.logger.info("Processed image sent successfully.")
        #print(jpg_as_text)
        return jpg_as_text


    except Exception as e:
        app.logger.error(f"Error during image processing: {e}")

'''
def main():
    try:
        #await sio.connect('http://121.159.74.206:8888', transports=['websocket'])
        await sio.connect('http://192.168.1.23:8888', transports=['websocket'])
        await sio.wait()  # 서버의 이벤트를 대기
    except Exception as e:
        logger.error(f"Socket connection error: {e}")
    finally:
        face_mesh.close()
        executor.shutdown(wait=True)
        logger.info("Resources have been cleaned up.")


# 서버와 연결 및 대기
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

'''