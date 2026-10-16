-- 阶段 0：数据库与应用账号初始化
-- 执行方式：mysql -u root -p < db/00_create_database.sql
--
-- 说明：应用不使用 root 账号，而是使用只对 zimeiti 库有权限的专用账号（最小权限原则）。

-- 1. 建库（utf8mb4 以支持完整的 Unicode，包括 emoji）
CREATE DATABASE IF NOT EXISTS zimeiti
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_general_ci;

-- 2. 建应用专用账号（仅本机可连）
CREATE USER IF NOT EXISTS 'zimeiti'@'localhost' IDENTIFIED BY 'zimeiti2026';

-- 3. 只授予 zimeiti 库的权限，不授予全局权限
GRANT ALL PRIVILEGES ON zimeiti.* TO 'zimeiti'@'localhost';

FLUSH PRIVILEGES;

-- 4. 验证
SELECT '数据库与账号创建完成' AS 结果;
SHOW DATABASES LIKE 'zimeiti';
