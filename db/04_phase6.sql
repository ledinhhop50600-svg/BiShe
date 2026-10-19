-- ================================================================
-- 阶段 6 增量脚本（2026-10-19）
-- 用于**已经建好的** zimeiti 库：给适配记录加版本号、按核对结果修正平台约束、
-- 给审核员补上"跨平台适配"菜单。
-- 新装环境不需要执行本脚本 —— 02_schema.sql / 03_seed.sql 已包含这些内容。
-- 本脚本可重复执行（ALTER 做了存在性判断，INSERT 用 IGNORE）。
-- 执行：mysql -uzimeiti -pzimeiti2026 --default-character-set=utf8mb4 zimeiti < db/04_phase6.sql
-- ================================================================

SET NAMES utf8mb4;

-- 1) 适配记录增加版本号：同一稿件在同一平台每生成一次 +1
SET @col_exists = (
    SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'audit_adaptation'
      AND column_name = 'version'
);
SET @ddl = IF(@col_exists = 0,
    'ALTER TABLE audit_adaptation ADD COLUMN version INT NOT NULL DEFAULT 1 COMMENT ''同一稿件的第几次适配（同一平台每生成一次 +1，便于回看历史版本）'' AFTER compliance_check',
    'SELECT ''version 列已存在，跳过'' AS msg');
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2) 按 2026-10-19 核对结果修正平台约束
--    微博：2016 年起原创微博上限 2000 字（信息流只展示前 140 字，风格要求重点前置）
UPDATE audit_platform
SET content_max_len = 2000,
    style_desc = '简短直接，重点放在前 140 字（信息流只展示前 140 字）'
WHERE platform_key = 'weibo';

--    B站：本系统按视频投稿处理（标题 80 / 简介 2000）；专栏是另一套规格
UPDATE audit_platform
SET style_desc = '视频投稿：标题口语化但说清主题，简介说明内容看点'
WHERE platform_key = 'bilibili';

-- 3) 审核员也具备创作能力，补上跨平台适配菜单（与"我的稿件/去投稿"一致）
INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (2, 43);

-- 4) 核对
SELECT platform_key, title_max_len, content_max_len, tag_rule, style_desc
FROM audit_platform ORDER BY sort;
