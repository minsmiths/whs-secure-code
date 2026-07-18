"""안전한 이미지 업로드 공통 유틸 (상품/채팅 공용).

보안 포인트:
- 확장자 화이트리스트 검사 (설정의 ALLOWED_IMAGE_EXTENSIONS)
- 원본 파일명을 신뢰하지 않고 무작위 파일명으로 재생성 → 경로 조작/덮어쓰기 방지
- 저장 위치는 설정의 UPLOAD_FOLDER 로 고정
"""
import os
import secrets

from flask import current_app
from werkzeug.utils import secure_filename


def allowed_image(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def save_image(file_storage) -> str | None:
    """업로드된 이미지를 저장하고 static 기준 상대경로(uploads/xxx)를 반환.

    파일이 없으면 None, 허용되지 않은 형식이면 ValueError.
    """
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_image(file_storage.filename):
        raise ValueError("허용되지 않은 이미지 형식입니다. (png, jpg, jpeg, gif, webp)")

    ext = secure_filename(file_storage.filename).rsplit(".", 1)[1].lower()
    random_name = f"{secrets.token_hex(16)}.{ext}"
    save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], random_name)
    file_storage.save(save_path)
    return f"uploads/{random_name}"
