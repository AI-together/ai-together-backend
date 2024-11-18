import os
import cv2
import numpy as np
import imutils


import cv2
import numpy as np
import imutils

def take_pictures_start(filter_image_path, image, x, y, filter_width, filter_height, deg):
    # 입력 이미지와 필터의 유효성 체크
    if not filter_image_path or filter_width < 5 or filter_height < 5:
        return image

    # 이미지를 복사하지 않고 직접 처리
    x, y = int(x), int(y)
    i_h, i_w, _ = image.shape
    filter_width, filter_height = int(filter_width / 2), int(filter_height / 2)

    # 필터 이미지 불러오기 및 크기 조정
    filter_image = cv2.imread(filter_image_path, cv2.IMREAD_UNCHANGED)
    if filter_image is None:
        print("필터 이미지를 불러올 수 없습니다.")
        return image

    filter_image = cv2.resize(filter_image, (filter_width * 2, filter_height * 2))
    filter_image = imutils.rotate_bound(filter_image, deg)

    # 필터 이미지에서 RGB 및 Alpha 채널 분리
    filter_rgb = filter_image[:, :, :3]
    filter_alpha = filter_image[:, :, 3] / 255

    h, w, _ = filter_image.shape

    # 필터의 위치 계산 (이미지 크기에서 벗어나지 않도록 조정)
    top_left_x = max(0, x - w // 2)
    top_left_y = max(0, y - h // 2)
    bottom_right_x = min(i_w, x + w // 2)
    bottom_right_y = min(i_h, y + h // 2)

    # 필터의 좌표 조정
    filter_top_left_x = max(0, (w // 2) - x)
    filter_top_left_y = max(0, (h // 2) - y)
    filter_bottom_right_x = filter_top_left_x + (bottom_right_x - top_left_x)
    filter_bottom_right_y = filter_top_left_y + (bottom_right_y - top_left_y)

    # 필터가 적용될 부분 계산
    if (0 <= top_left_x < bottom_right_x <= i_w and
        0 <= top_left_y < bottom_right_y <= i_h and
        0 <= filter_top_left_x < filter_bottom_right_x <= w and
        0 <= filter_top_left_y < filter_bottom_right_y <= h):

        # 필터 영역을 한 번에 적용 (벡터화)
        roi = image[top_left_y:bottom_right_y, top_left_x:bottom_right_x]
        filter_area = filter_rgb[filter_top_left_y:filter_bottom_right_y, filter_top_left_x:filter_bottom_right_x]
        alpha = filter_alpha[filter_top_left_y:filter_bottom_right_y, filter_top_left_x:filter_bottom_right_x]

        # 필터 합성 (벡터화된 방식으로 채널 별로 합성)
        roi[:] = (filter_area * alpha[..., None] + roi * (1 - alpha[..., None]))

    return image



def frame_image(image, frame_image_path):
    if frame_image_path == 0:
        return image

    i_h, i_w, _ = image.shape
    frame_image = cv2.imread(frame_image_path, cv2.IMREAD_UNCHANGED)
    frame_image = cv2.resize(frame_image, (i_w, i_h))

    frame_rgb = frame_image[:, :, :3]
    frame_alpha = frame_image[:, :, 3] / 255

    # 프레임 합성 연산을 벡터화하여 속도 개선
    for i in range(3):
        image[:, :, i] = (frame_rgb[:, :, i] * frame_alpha + image[:, :, i] * (1 - frame_alpha))

    return image


def pull_image(save_image, count):
    if count < 4:
        save_image = cv2.flip(save_image, 1)
        cv2.imwrite(f"{count}_filter_image.jpg", save_image)
        print("이미지 저장 완료")

    elif count == 4:
        save_image = cv2.flip(save_image, 1)
        cv2.imwrite(f"{count}_filter_image.jpg", save_image)
        print("이미지 촬영 종료")

    else:
        raise ValueError(f"인생 4컷 임마 인생 4컷 인생 {count}컷이 아니라")
    return 0
