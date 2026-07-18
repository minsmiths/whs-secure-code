# 🎾 Deuce Market — 테니스 용품 중고거래 플랫폼

Flask + SQLite 기반의 소규모 중고거래 플랫폼입니다.
**WHS Secure Coding** 실습 과제로, 개발 전 과정에서 시큐어 코딩을 적용하는 것을 목표로 합니다.

> Tiny Second-hand Shopping Platform — 테니스 라켓 · 스트링 · 신발 · 의류 등을 사고파는 플랫폼

---

## ✨ 주요 기능

- **회원 관리** — 회원가입 / 로그인 / 로그아웃 / 마이페이지(소개글·비밀번호 변경) / 사용자 프로필 조회
- **상품 관리** — 상품 등록(이미지 업로드) / 목록 / 상세 / 내 상품 관리 / 삭제
- **검색** — 상품명·설명 검색, 카테고리 필터
- (예정) 실시간 채팅, 유저 간 송금, 신고/차단, 관리자 페이지

## 🔐 적용된 보안 요소 (기본 뼈대 기준)

| 위협 | 대응 |
|------|------|
| SQL Injection | 모든 쿼리 파라미터 바인딩(`?`) 사용 |
| XSS | Jinja2 자동 이스케이프, CSP 헤더 |
| CSRF | Flask-WTF `CSRFProtect` 전역 적용 (모든 POST에 토큰 검증) |
| 비밀번호 유출 | 평문 저장 금지, Werkzeug PBKDF2 해싱 |
| 세션 탈취 | 쿠키 `HttpOnly` / `SameSite=Lax` / (운영 시)`Secure`, 로그인 시 세션 재발급 |
| 접근제어(IDOR) | `login_required` / 소유자 검증 후 상품 삭제 |
| 파일 업로드 | 확장자 화이트리스트, 파일명 무작위 재생성, 5MB 제한 |
| 민감정보 하드코딩 | `SECRET_KEY` 등 환경 변수(`.env`)로 분리, 운영 시 필수화 |
| 클릭재킹/스니핑 | `X-Frame-Options`, `X-Content-Type-Options` 헤더 |

---

## ⚙️ 환경 설정 및 실행 방법

### 1. 요구 사항
- Python 3.10 이상

### 2. 설치

```bash
# 저장소 클론
git clone <this-repo-url>
cd whs-secure-code

# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 3. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 열어 SECRET_KEY 값을 랜덤 값으로 변경
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. 데이터베이스 초기화 (+ 샘플 데이터)

```bash
export FLASK_APP=run.py          # Windows(PowerShell): $env:FLASK_APP="run.py"
flask init-db                    # 테이블 생성
flask seed                       # (선택) 관리자 계정 + 샘플 상품 생성
```

`flask seed` 실행 시 기본 계정:
- 관리자: `admin` / `admin-Deuce-2026!` (환경변수 `ADMIN_PASSWORD`로 변경 가능)
- 샘플 판매자: `tennislover` / `password-1234!`

> ⚠️ 데모용 계정이므로 실제 배포 시 반드시 삭제/변경하세요.

### 5. 서버 실행

```bash
python run.py
```

→ 브라우저에서 http://127.0.0.1:5000 접속

---

## 📁 프로젝트 구조

```
whs-secure-code/
├── run.py                 # 개발 서버 진입점
├── config.py              # 설정 (보안 기본값 secure-by-default)
├── requirements.txt
├── .env.example           # 환경 변수 템플릿
├── app/
│   ├── __init__.py        # 애플리케이션 팩토리 + 보안 헤더/CSRF
│   ├── db.py              # SQLite 커넥션 관리
│   ├── schema.sql         # DB 스키마
│   ├── security.py        # 인증/인가 유틸 (login_required 등)
│   ├── auth.py            # 회원가입/로그인/마이페이지
│   ├── products.py        # 상품 CRUD + 검색
│   ├── main.py            # 홈
│   ├── seed.py            # 데모 데이터 CLI
│   ├── templates/         # Jinja2 템플릿
│   └── static/            # CSS, 업로드 이미지
└── instance/              # DB 파일 (git 미포함)
```

---

## 🧪 테스트 (체크리스트 기반)

기능 및 보안 요소별 체크리스트는 개발 보고서에 정리되어 있습니다.
간단 확인:

```bash
# 로그인 없이 상품등록 접근 → 로그인 페이지로 리다이렉트되는지
curl -i http://127.0.0.1:5000/products/new

# CSRF 토큰 없는 POST → 400 차단되는지
curl -i -X POST http://127.0.0.1:5000/auth/register -d "username=x&password=xxxxxxxx"
```

---

## 📄 라이선스 / 참고

- 실습 베이스: [ugonfor/secure-coding](https://github.com/ugonfor/secure-coding)
- WHS Secure Coding 과제 제출용
