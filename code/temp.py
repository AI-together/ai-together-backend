import cv2

# 이미지 불러오기
def img_connect(background_img, image1_img, image2_img):
    background = cv2.imread(background_img)  # 배경 이미지
    image1 = cv2.imread(image1_img)  # 합성할 첫 번째 이미지
    image2 = cv2.imread(image2_img)  # 합성할 두 번째 이미지

    # 이미지가 제대로 불러와졌는지 확인
    if background is None or image1 is None or image2 is None:
        print("이미지를 불러올 수 없습니다. 경로를 확인해 주세요.")
    else:
        # 각 이미지의 크기 조절 (원하는 크기로 조절 가능)
        background = cv2.resize(background, (300, 450))

        image1 = cv2.resize(image1, (266, 160))
        image2 = cv2.resize(image2, (266, 160))


        # 첫 번째 이미지 위치 설정 (배경 위에서 좌상단 위치 x, y)
        x1, y1 = 17, 15  # 첫 번째 이미지를 배경의 (100, 100) 위치에 배치
        background[y1:y1 + image1.shape[0], x1:x1 + image1.shape[1]] = image1


        # 두 번째 이미지 위치 설정 (배경 위에서 좌상단 위치 x, y)
        x2, y2 = 17, 190  # 두 번째 이미지를 배경의 (400, 300) 위치에 배치
        background[y2:y2 + image2.shape[0], x2:x2 + image2.shape[1]] = image2


        # 결과 이미지 저장
        cv2.imwrite('img/end.jpg', background)

        # 결과 이미지 확인 (선택 사항)
        cv2.imshow('Combined Image', background)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

#img_connect('img/background.png', 'img/img1.jpg', 'img/img2.jpg')