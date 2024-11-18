import os

# 필터 번호가 0이면 None을 반환하고, 그렇지 않으면 파일 경로를 반환
def checknumber(filter_number):
    FILTER_DIRECTORY = r'C:\Users\kyle0\Desktop\trick-or-picture-main\trick-or-picture-main\img'  # 필터 이미지 디렉토리
    if filter_number == 0:
        return None

    filter_image_path = os.path.join(FILTER_DIRECTORY, f"{filter_number}.png")  # 경로 안전하게 결합
    print(f"Trying to find filter image at: {filter_image_path}")

    if os.path.isfile(filter_image_path):
        print("OK")
        return filter_image_path
    else:
        print(f"File does not exist: {filter_image_path}")
        return None
