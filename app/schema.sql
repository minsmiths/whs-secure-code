-- ============================================================
--  Deuce Market 🎾  데이터베이스 스키마
--  테니스 용품 중고거래 플랫폼
-- ============================================================

PRAGMA foreign_keys = ON;

-- 기존 테이블 제거 (초기화용)
DROP TABLE IF EXISTS transfer;
DROP TABLE IF EXISTS report;
DROP TABLE IF EXISTS message;
DROP TABLE IF EXISTS product;
DROP TABLE IF EXISTS user;

-- ----------------------------------------------------------------
-- 사용자
--   password_hash: 평문이 아닌 해시로만 저장 (Werkzeug PBKDF2)
--   balance: 유저 간 송금용 잔액
--   is_active: 신고 누적 시 0(휴면)으로 전환
--   is_admin: 관리자 여부
-- ----------------------------------------------------------------
CREATE TABLE user (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    bio           TEXT    NOT NULL DEFAULT '',
    balance       INTEGER NOT NULL DEFAULT 0,
    is_active     INTEGER NOT NULL DEFAULT 1,
    is_admin      INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------
-- 상품 (테니스 용품)
--   category: 라켓 / 스트링 / 신발 / 의류 / 가방 / 공 / 액세서리
--   status: active(판매중) / sold(판매완료) / blocked(신고차단)
-- ----------------------------------------------------------------
CREATE TABLE product (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    description TEXT    NOT NULL DEFAULT '',
    price       INTEGER NOT NULL CHECK (price >= 0),
    category    TEXT    NOT NULL DEFAULT '기타',
    image_path  TEXT,
    status      TEXT    NOT NULL DEFAULT 'active',
    seller_id   INTEGER NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (seller_id) REFERENCES user (id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------
-- 채팅 메시지 (전체 채팅 + 1:1 채팅)
--   recipient_id 가 NULL 이면 전체 채팅, 값이 있으면 1:1 채팅
-- ----------------------------------------------------------------
CREATE TABLE message (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id    INTEGER NOT NULL,
    recipient_id INTEGER,
    body         TEXT    NOT NULL,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (sender_id)    REFERENCES user (id) ON DELETE CASCADE,
    FOREIGN KEY (recipient_id) REFERENCES user (id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------
-- 신고 (유저 또는 상품 대상)
--   target_type: 'user' 또는 'product'
--   같은 사람이 같은 대상을 중복 신고하지 못하도록 UNIQUE 제약
-- ----------------------------------------------------------------
CREATE TABLE report (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter_id INTEGER NOT NULL,
    target_type TEXT    NOT NULL CHECK (target_type IN ('user', 'product')),
    target_id   INTEGER NOT NULL,
    reason      TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (reporter_id) REFERENCES user (id) ON DELETE CASCADE,
    UNIQUE (reporter_id, target_type, target_id)
);

-- ----------------------------------------------------------------
-- 송금 내역 (유저 간 잔액 이체)
-- ----------------------------------------------------------------
CREATE TABLE transfer (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id   INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    amount      INTEGER NOT NULL CHECK (amount > 0),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (sender_id)   REFERENCES user (id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES user (id) ON DELETE CASCADE
);

-- 조회 성능을 위한 인덱스
CREATE INDEX idx_product_seller  ON product (seller_id);
CREATE INDEX idx_product_status  ON product (status);
CREATE INDEX idx_message_recipient ON message (recipient_id);
CREATE INDEX idx_report_target    ON report (target_type, target_id);
