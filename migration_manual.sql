-- ============================================================
-- IoT Data Platform 精准迁移脚本 (v2)
-- ============================================================
-- 基于真实模型(models/database.py)生成的列清单
-- 关键改进:
--   1. 用存储过程 + INFORMATION_SCHEMA 检测列是否存在
--   2. 重复执行不会报错
--   3. 列定义完全匹配模型
-- ============================================================

SET NAMES utf8mb4;

-- 删掉可能存在的旧过程
DROP PROCEDURE IF EXISTS add_column_if_missing;

DELIMITER //

CREATE PROCEDURE add_column_if_missing(
    IN p_table VARCHAR(64),
    IN p_column VARCHAR(64),
    IN p_definition VARCHAR(255)
)
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = p_table
          AND COLUMN_NAME = p_column
    ) THEN
        SET @sql = CONCAT('ALTER TABLE `', p_table, '` ADD COLUMN `', p_column, '` ', p_definition);
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
        SELECT CONCAT('✅ 已添加 ', p_table, '.', p_column) AS result;
    ELSE
        SELECT CONCAT('⏭️  ', p_table, '.', p_column, ' 已存在,跳过') AS result;
    END IF;
END //

DELIMITER ;

-- ============================================================
-- 1. users 表 (id, username, email, password_hash, is_active, is_admin, created_at, last_login)
-- ============================================================
CALL add_column_if_missing('users', 'last_login', 'DATETIME NULL');

-- ============================================================
-- 2. devices 表 (id, name, custom_name, voltage_mv, category_id, user_id, is_online, last_seen, first_seen, total_packets)
-- ============================================================
CALL add_column_if_missing('devices', 'last_seen', 'DATETIME NULL');

-- ============================================================
-- 3. channels 表 (id, device_id, name, is_online, last_seen, first_seen)
-- ============================================================
-- 全部已在模型中,但保险起见都补一下
CALL add_column_if_missing('channels', 'last_seen', 'DATETIME NULL');
CALL add_column_if_missing('channels', 'first_seen', 'DATETIME NULL');

-- ============================================================
-- 4. data_points 表 (id, channel_id, name, value, last_value, last_updated, update_count)
-- ============================================================
CALL add_column_if_missing('data_points', 'last_value', 'FLOAT DEFAULT 0.0');
CALL add_column_if_missing('data_points', 'last_updated', 'DATETIME NULL');
CALL add_column_if_missing('data_points', 'update_count', 'INT DEFAULT 0');

-- ============================================================
-- 5. data_history 表 (id, data_point_id, device_id, channel_id, value, timestamp)
-- ============================================================
-- 全部已在模型中

-- ============================================================
-- 6. dashboard_widgets 表 (id, user_id, device_id, channel_id, data_point_id, sort_order, is_visible, color, created_at)
-- ============================================================
-- 全部已在模型中

-- ============================================================
-- 7. tcp_server_configs 表 (id, name, port, host, is_active, description, created_at, last_started, total_connections, total_messages, error_count)
-- ============================================================
CALL add_column_if_missing('tcp_server_configs', 'last_started', 'DATETIME NULL');
CALL add_column_if_missing('tcp_server_configs', 'total_connections', 'INT DEFAULT 0');
CALL add_column_if_missing('tcp_server_configs', 'total_messages', 'INT DEFAULT 0');
CALL add_column_if_missing('tcp_server_configs', 'error_count', 'INT DEFAULT 0');

-- ============================================================
-- 8. tcp_logs 表 (id, port, client_ip, direction, content, status, error_message, timestamp)
-- ============================================================
-- 全部已在模型中

-- ============================================================
-- 9. system_configs 表 (id, key, value, description, updated_at)
-- ============================================================
-- 全部已在模型中

-- ============================================================
-- 10. login_logs 表 (id, user_id, username, ip, user_agent, status, timestamp) ❗ 缺 ip 列
-- ============================================================
CALL add_column_if_missing('login_logs', 'ip', 'VARCHAR(50) NULL');
CALL add_column_if_missing('login_logs', 'user_agent', 'VARCHAR(255) NULL');

-- ============================================================
-- 验证关键表
-- ============================================================
SELECT '===================== 验证 users 表 =====================' AS step;
DESCRIBE users;

SELECT '===================== 验证 devices 表 =====================' AS step;
DESCRIBE devices;

SELECT '===================== 验证 login_logs 表 =====================' AS step;
DESCRIBE login_logs;

SELECT '===================== 验证 data_points 表 =====================' AS step;
DESCRIBE data_points;

SELECT '✅ 全部迁移完成' AS done;
