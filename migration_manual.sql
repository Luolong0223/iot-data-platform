-- ============================================================
-- IoT Data Platform 数据库手动迁移脚本
-- ============================================================
-- 用途: 修复 "Unknown column 'xxx' in 'field list'" 错误
-- 用法: 在 MySQL 客户端中执行 (需有 ALTER 权限)
--   mysql -u iot-platform -p iot-platform < migration_manual.sql
-- 或登录后 use iot-platform; 然后 source migration_manual.sql
-- ============================================================

-- ⚠️ 建议先执行 SELECT 检查表是否存在,再决定是否 ALTER
-- ⚠️ 部分列可能已存在,执行会报 "Duplicate column name",可以忽略

SET NAMES utf8mb4;

-- ============================================================
-- 1. users 表
-- ============================================================
ALTER TABLE `users` ADD COLUMN `last_login` DATETIME NULL;
ALTER TABLE `users` ADD COLUMN `updated_at` DATETIME NULL;

-- ============================================================
-- 2. devices 表
-- ============================================================
ALTER TABLE `devices` ADD COLUMN `custom_name` VARCHAR(120) NULL;
ALTER TABLE `devices` ADD COLUMN `description` VARCHAR(500) NULL;
ALTER TABLE `devices` ADD COLUMN `first_seen` DATETIME NULL;
ALTER TABLE `devices` ADD COLUMN `category_id` INT NULL;
ALTER TABLE `devices` ADD COLUMN `user_id` INT NULL;
ALTER TABLE `devices` ADD COLUMN `updated_at` DATETIME NULL;

-- ============================================================
-- 3. channels 表
-- ============================================================
ALTER TABLE `channels` ADD COLUMN `first_seen` DATETIME NULL;
ALTER TABLE `channels` ADD COLUMN `updated_at` DATETIME NULL;

-- ============================================================
-- 4. data_points 表
-- ============================================================
ALTER TABLE `data_points` ADD COLUMN `last_value` FLOAT NULL;
ALTER TABLE `data_points` ADD COLUMN `last_updated` DATETIME NULL;
ALTER TABLE `data_points` ADD COLUMN `update_count` INT NULL;
ALTER TABLE `data_points` ADD COLUMN `unit` VARCHAR(20) NULL;

-- ============================================================
-- 5. data_history 表
-- ============================================================
ALTER TABLE `data_history` ADD COLUMN `unit` VARCHAR(20) NULL;

-- ============================================================
-- 6. device_categories 表
-- ============================================================
ALTER TABLE `device_categories` ADD COLUMN `description` VARCHAR(500) NULL;
ALTER TABLE `device_categories` ADD COLUMN `sort_order` INT DEFAULT 0;

-- ============================================================
-- 7. dashboard_widgets 表
-- ============================================================
ALTER TABLE `dashboard_widgets` ADD COLUMN `data_point_id` INT NULL;
ALTER TABLE `dashboard_widgets` ADD COLUMN `device_id` INT NULL;
ALTER TABLE `dashboard_widgets` ADD COLUMN `channel_id` INT NULL;
ALTER TABLE `dashboard_widgets` ADD COLUMN `sort_order` INT DEFAULT 0;
ALTER TABLE `dashboard_widgets` ADD COLUMN `is_visible` TINYINT(1) DEFAULT 1;
ALTER TABLE `dashboard_widgets` ADD COLUMN `current_value` FLOAT NULL;
ALTER TABLE `dashboard_widgets` ADD COLUMN `last_updated` DATETIME NULL;

-- ============================================================
-- 8. tcp_server_configs 表
-- ============================================================
ALTER TABLE `tcp_server_configs` ADD COLUMN `enabled` TINYINT(1) DEFAULT 1;
ALTER TABLE `tcp_server_configs` ADD COLUMN `status` VARCHAR(20) DEFAULT 'stopped';

-- ============================================================
-- 9. tcp_logs 表
-- ============================================================
ALTER TABLE `tcp_logs` ADD COLUMN `device_ip` VARCHAR(45) NULL;
ALTER TABLE `tcp_logs` ADD COLUMN `device_port` INT NULL;
ALTER TABLE `tcp_logs` ADD COLUMN `server_port` INT NULL;
ALTER TABLE `tcp_logs` ADD COLUMN `direction` VARCHAR(10) DEFAULT 'in';
ALTER TABLE `tcp_logs` ADD COLUMN `payload` TEXT NULL;

-- ============================================================
-- 10. system_configs 表
-- ============================================================
ALTER TABLE `system_configs` ADD COLUMN `description` VARCHAR(500) NULL;
ALTER TABLE `system_configs` ADD COLUMN `updated_at` DATETIME NULL;

-- ============================================================
-- 11. login_logs 表
-- ============================================================
ALTER TABLE `login_logs` ADD COLUMN `user_agent` VARCHAR(255) NULL;
ALTER TABLE `login_logs` ADD COLUMN `timestamp` DATETIME NULL;
ALTER TABLE `login_logs` ADD COLUMN `status` VARCHAR(20) NULL;

-- ============================================================
-- 12. roles 表
-- ============================================================
ALTER TABLE `roles` ADD COLUMN `description` VARCHAR(500) NULL;

-- ============================================================
-- 13. permissions 表
-- ============================================================
ALTER TABLE `permissions` ADD COLUMN `description` VARCHAR(500) NULL;

-- ============================================================
-- 14. user_roles 表
-- ============================================================
ALTER TABLE `user_roles` ADD COLUMN `granted_at` DATETIME NULL;

-- ============================================================
-- 验证: 列出 users 表的列
-- ============================================================
DESCRIBE `users`;

SELECT '✅ 手动迁移脚本执行完成' AS message;
SELECT '如遇 Duplicate column name 错误,说明该列已存在,可忽略' AS note;
