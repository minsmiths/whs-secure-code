-- ============================================================
--  Deuce Market 🎾  데이터베이스 스키마
--  테니스 용품 중고거래 플랫폼 (프리미엄 리디자인)
-- ============================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS message_reaction;
DROP TABLE IF EXISTS message;
DROP TABLE IF EXISTS conversation;
DROP TABLE IF EXISTS favorite;
DROP TABLE IF EXISTS transfer;
DROP TABLE IF EXISTS report;
DROP TABLE IF EXISTS product;
DROP TABLE IF EXISTS user;

-- ----------------------------------------------------------------
-- 사용자
-- ----------------------------------------------------------------
CREATE TABLE user (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    bio           TEXT    NOT NULL DEFAULT '',
    region        TEXT    NOT NULL DEFAULT '',
    rating        REAL    NOT NULL DEFAULT 5.0,
    balance       INTEGER NOT NULL DEFAULT 0,
    is_active     INTEGER NOT NULL DEFAULT 1,
    is_admin      INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------
-- 상품 (테니스 용품)
--   status: active(판매중) / sold(판매완료) / blocked(신고차단)
-- ----------------------------------------------------------------
CREATE TABLE product (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT    NOT NULL,
    description     TEXT    NOT NULL DEFAULT '',
    price           INTEGER NOT NULL CHECK (price >= 0),
    category        TEXT    NOT NULL DEFAULT '기타',
    brand           TEXT    NOT NULL DEFAULT '',
    condition_grade TEXT    NOT NULL DEFAULT '',
    usage_period    TEXT    NOT NULL DEFAULT '',
    grip            TEXT    NOT NULL DEFAULT '',
    location        TEXT    NOT NULL DEFAULT '',
    image_path      TEXT,
    status          TEXT    NOT NULL DEFAULT 'active',
    seller_id       INTEGER NOT NULL,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (seller_id) REFERENCES user (id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------
-- 찜 (좋아요)
-- ----------------------------------------------------------------
CREATE TABLE favorite (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id)    REFERENCES user (id)    ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES product (id) ON DELETE CASCADE,
    UNIQUE (user_id, product_id)
);

-- ----------------------------------------------------------------
-- 채팅방 (구매자 ↔ 판매자, 상품 단위 1:1)
--   buyer_hidden/seller_hidden: 각자 '채팅방 나가기' 시 1 (목록에서 숨김)
--   *_read_at: 각자 마지막으로 읽은 시각 (안읽음 카운트 계산용)
-- ----------------------------------------------------------------
CREATE TABLE conversation (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id     INTEGER NOT NULL,
    buyer_id       INTEGER NOT NULL,
    seller_id      INTEGER NOT NULL,
    buyer_hidden   INTEGER NOT NULL DEFAULT 0,
    seller_hidden  INTEGER NOT NULL DEFAULT 0,
    buyer_read_at  TEXT,
    seller_read_at TEXT,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (product_id) REFERENCES product (id) ON DELETE CASCADE,
    FOREIGN KEY (buyer_id)   REFERENCES user (id)    ON DELETE CASCADE,
    FOREIGN KEY (seller_id)  REFERENCES user (id)    ON DELETE CASCADE,
    UNIQUE (product_id, buyer_id)
);

-- ----------------------------------------------------------------
-- 채팅 메시지 (특정 채팅방에 속함)
--   is_deleted: 카톡처럼 '삭제된 메시지입니다' 표시
--   edited_at : 수정 시각 (수정됨 표시)
-- ----------------------------------------------------------------
CREATE TABLE message (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    sender_id       INTEGER NOT NULL,
    body            TEXT    NOT NULL DEFAULT '',
    image_path      TEXT,
    is_deleted      INTEGER NOT NULL DEFAULT 0,
    edited_at       TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (conversation_id) REFERENCES conversation (id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id)       REFERENCES user (id)         ON DELETE CASCADE
);

-- ----------------------------------------------------------------
-- 메시지 공감 (카톡 공감처럼 한 유저당 1회 토글)
-- ----------------------------------------------------------------
CREATE TABLE message_reaction (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (message_id) REFERENCES message (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)    REFERENCES user (id)    ON DELETE CASCADE,
    UNIQUE (message_id, user_id)
);

-- ----------------------------------------------------------------
-- 신고
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
-- 송금 내역
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

CREATE INDEX idx_product_seller   ON product (seller_id);
CREATE INDEX idx_product_status   ON product (status);
CREATE INDEX idx_favorite_user    ON favorite (user_id);
CREATE INDEX idx_conv_buyer       ON conversation (buyer_id);
CREATE INDEX idx_conv_seller      ON conversation (seller_id);
CREATE INDEX idx_message_conv     ON message (conversation_id);
CREATE INDEX idx_reaction_message ON message_reaction (message_id);
CREATE INDEX idx_report_target    ON report (target_type, target_id);
