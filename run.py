"""개발 서버 실행 진입점.

  python run.py

운영 환경에서는 gunicorn 등 WSGI 서버 사용을 권장한다.
"""
import os

from dotenv import load_dotenv

# .env 파일을 먼저 로드 (SECRET_KEY 등)
load_dotenv()

from app import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    # debug 모드는 환경 변수로만 켜지도록 (기본 False → 운영 사고 방지)
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="127.0.0.1", port=5000, debug=debug)
