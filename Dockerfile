# 공식 Python 이미지를 사용 (특정 버전)
FROM python:3.11-slim

# 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 설치
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . /app/

# 애플리케이션이 실행되는 포트 노출
EXPOSE 8888

# 기본 명령어 설정
CMD ["python", "app.py"]
