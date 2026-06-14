# IoT 数据平台 - 部署指南

## 快速开始

### 方式一：Docker Compose 部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/Luolong0223/iot-data-platform.git
cd iot-data-platform

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f iot-platform
```

访问地址：http://localhost:5000

### 方式二：宝塔面板部署

```bash
# 1. 下载部署脚本
wget https://raw.githubusercontent.com/Luolong0223/iot-data-platform/main/deploy-baota.sh

# 2. 执行部署
chmod +x deploy-baota.sh
sudo bash deploy-baota.sh
```

### 方式三：手动部署

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 3. 初始化数据库
python -c "from app import create_app; from models.database import db; app = create_app(); app.app_context().push(); db.create_all()"

# 4. 启动服务
gunicorn --bind 0.0.0.0:5000 --workers 4 app:app
```

## 环境要求

- Python 3.8+
- MySQL 5.7+ / 8.0
- Redis 6.0+
- Nginx（可选，用于反向代理）

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| FLASK_ENV | 运行环境 | production |
| SECRET_KEY | 密钥 | 随机生成 |
| DATABASE_URL | 数据库连接 | mysql+pymysql://... |
| REDIS_URL | Redis 连接 | redis://localhost:6379/0 |

### 数据库配置

```bash
# MySQL
CREATE DATABASE `iot-platform` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'iot-platform'@'localhost' IDENTIFIED BY 'your-password';
GRANT ALL PRIVILEGES ON `iot-platform`.* TO 'iot-platform'@'localhost';
```

## 服务管理

### Docker Compose

```bash
# 启动
docker-compose up -d

# 停止
docker-compose down

# 重启
docker-compose restart

# 查看日志
docker-compose logs -f
```

### Systemd

```bash
# 启动
systemctl start iot-platform

# 停止
systemctl stop iot-platform

# 重启
systemctl restart iot-platform

# 查看状态
systemctl status iot-platform
```

## 常见问题

### 1. 数据库连接失败

检查 MySQL 服务是否启动，以及数据库用户权限是否正确。

### 2. Redis 连接失败

检查 Redis 服务是否启动，以及连接字符串是否正确。

### 3. 端口被占用

修改 docker-compose.yml 或 Nginx 配置中的端口映射。

## 性能优化

### 1. 启用 Gzip 压缩

Nginx 配置已包含 Gzip 压缩，无需额外配置。

### 2. 数据库索引

系统已自动创建必要的索引，如需优化可参考 `models/database.py`。

### 3. 缓存配置

Redis 缓存已默认启用，可通过 `REDIS_URL` 环境变量配置。

## 安全建议

1. 修改默认的 SECRET_KEY
2. 修改默认的数据库密码
3. 配置 HTTPS（使用 Let's Encrypt）
4. 限制数据库访问 IP
5. 定期备份数据库

## 备份与恢复

### 备份数据库

```bash
mysqldump -u iot-platform -p iot-platform > backup_$(date +%Y%m%d).sql
```

### 恢复数据库

```bash
mysql -u iot-platform -p iot-platform < backup_20240101.sql
```

## 技术支持

- GitHub Issues: https://github.com/Luolong0223/iot-data-platform/issues
- 文档: https://github.com/Luolong0223/iot-data-platform/wiki
