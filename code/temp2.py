import os
import base64
import qrcode

import os
import base64
import qrcode
from PIL import Image
from io import BytesIO

import os
import base64
import qrcode
from PIL import Image
from io import BytesIO

def convert_image_to_qr(image_path, output_path, max_size=(500, 500), quality=80):
    """
    이미지 파일을 리사이즈하고 압축하여 QR 코드로 변환하는 함수

    :param image_path: 변환할 이미지 경로
    :param output_path: 생성된 QR 코드 이미지 저장 경로
    :param max_size: 최대 크기 (가로, 세로)
    :param quality: 압축 품질 (0 ~ 100)
    """
    if not os.path.exists(image_path):
        print(f"이미지 파일이 존재하지 않습니다: {image_path}")
        return

    try:
        # 이미지 리사이즈
        img = Image.open(image_path)
        img.thumbnail(max_size)  # 이미지 크기 축소

        # 이미지 압축 (JPEG로 저장하며 품질을 설정)
        with BytesIO() as buffer:
            img.save(buffer, format="JPEG", quality=quality)  # JPEG 형식으로 압축
            image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

        # QR 코드 생성
        qr = qrcode.QRCode(
            version=1,  # QR 코드 크기
            error_correction=qrcode.constants.ERROR_CORRECT_L,  # 오류 보정
            box_size=10,
            border=4,
        )
        qr.add_data(image_data)
        qr.make(fit=True)

        # QR 코드 이미지 생성 및 저장
        qr_image = qr.make_image(fill_color="black", back_color="white")
        qr_image.save(output_path)
        print(f"QR 코드가 생성되었습니다: {output_path}")

    except Exception as e:
        print(f"오류 발생: {e}")




convert_image_to_qr("../res_img/res.png", "../qrcode/qr.png")