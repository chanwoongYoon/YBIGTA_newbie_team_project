CREATE DATABASE IF NOT EXISTS review_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE review_db;

CREATE TABLE IF NOT EXISTS reviews (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  source          VARCHAR(20)  NOT NULL COMMENT 'goodreads / yes24 / kyobo',
  review_key      VARCHAR(200) NOT NULL COMMENT '사이트 내 고유 식별값',
  stars           FLOAT,
  review          TEXT,
  review_date     DATE,
  sentiment_label VARCHAR(20),
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  collected_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_source_review (source, review_key),
  INDEX idx_review_date (review_date),
  INDEX idx_source (source),
  INDEX idx_collected_at (collected_at)
) ENGINE=InnoDB;