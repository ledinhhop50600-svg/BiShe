-- ================================================================
-- 阶段 7 增量脚本（2026-10-19）
-- 用于**已经建好的** zimeiti 库：给审核记录增加内容哈希。
-- 新装环境不需要执行本脚本 —— 02_schema.sql 已包含该列。
-- 可重复执行（ALTER 做了存在性判断）。
-- 执行：mysql -uzimeiti -pzimeiti2026 --default-character-set=utf8mb4 zimeiti < db/05_phase7.sql
-- ================================================================

SET NAMES utf8mb4;

SET @col_exists = (
    SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'audit_record'
      AND column_name = 'content_hash'
);
SET @ddl = IF(@col_exists = 0,
    'ALTER TABLE audit_record ADD COLUMN content_hash VARCHAR(64) DEFAULT NULL COMMENT ''判定时稿件标题+正文的 SHA-256；内容改过则本记录视为过期'' AFTER violation_fragments',
    'SELECT ''content_hash 列已存在，跳过'' AS msg');
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT COUNT(*) AS audit_record_has_content_hash
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'audit_record'
  AND column_name = 'content_hash';
