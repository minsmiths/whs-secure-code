"""안전한 이미지 업로드 공통 유틸 (상품/채팅 공용).

보안 포인트:
- 확장자 화이트리스트 검사 (설정의 ALLOWED_IMAGE_EXTENSIONS)
- 원본 파일명을 신뢰하지 않고 무작위 파일명으로 재생성 → 경로 조작/덮어쓰기 방지
- 저장 위치는 설정의 UPLOAD_FOLDER 로 고정
"""
import os
import secrets

from flask import current_app


def _extract_ext(filename: str) -> str | None:
    """원본 파일명에서 확장자만 소문자로 추출 (없으면 None)."""
    if not filename or "." not in filename:
        return None
    return filename.rsplit(".", 1)[1].strip().lower()


def allowed_image(filename: str) -> bool:
    ext = _extract_ext(filename)
    return ext is not None and ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def _sniff_image_type(header: bytes) -> str | None:
    """파일 앞부분(매직 바이트)으로 실제 이미지 형식을 추정. 모르면 None."""
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return "gif"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


def save_image(file_storage) -> str | None:
    """업로드된 이미지를 저장하고 static 기준 상대경로(uploads/xxx)를 반환.

    파일이 없으면 None, 허용되지 않은 형식이면 ValueError.

    - 확장자는 '원본 파일명'에서 추출해 화이트리스트로 검증한다.
      (secure_filename 은 한글 등 비ASCII 파일명에서 확장자까지 제거해
       IndexError 를 유발하므로 확장자 추출에 사용하지 않는다.)
    - 실제 저장 파일명은 무작위(token_hex)로 생성 → 원본 파일명을 신뢰하지 않고
      경로 조작/덮어쓰기를 방지한다. 검증된 확장자만 ASCII 로 재사용한다.
    """
    if not file_storage or file_storage.filename == "":
        return None

    ext = _extract_ext(file_storage.filename)
    if ext is None or ext not in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]:
        raise ValueError("허용되지 않은 이미지 형식입니다. (png, jpg, jpeg, gif, webp)")

    # 파일 '내용'(매직 바이트)이 실제 이미지인지 확인 → 확장자 위장 업로드 차단
    header = file_storage.stream.read(16)
    file_storage.stream.seek(0)
    sniffed = _sniff_image_type(header)
    if sniffed is None:
        raise ValueError("이미지 파일이 아닙니다. (내용 검증 실패)")

    random_name = f"{secrets.token_hex(16)}.{ext}"
    save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], random_name)
    file_storage.save(save_path)
    return f"uploads/{random_name}"
