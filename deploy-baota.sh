#!/bin/bash
# IoT 数据平台 - 宝塔面板一键部署脚本
# 使用方法: bash deploy-baota.sh

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  IoT 数据平台 - 宝塔面板部署脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}请使用 root 用户运行此脚本${NC}"
    exit 1
fi

# 检查宝塔面板是否安装
if [ ! -f "/www/server/panel/BT-Panel" ]; then
    echo -e "${YELLOW}未检测到宝塔面板，正在安装...${NC}"
    wget -O install.sh http://download.bt.cn/install/install-ubuntu_6.0.sh && sudo bash install.sh
fi

# 安装必要软件
echo -e "${GREEN}[1/6] 安装必要软件...${NC}"
bt install nginx
bt install mysql
bt install redis
bt install python_manager

# 创建项目目录
PROJECT_DIR="/www/wwwroot/iot-platform"
echo -e "${GREEN}[2/6] 创建项目目录: ${PROJECT_DIR}${NC}"
mkdir -p ${PROJECT_DIR}
cd ${PROJECT_DIR}

# 克隆代码
echo -e "${GREEN}[3/6] 克隆项目代码...${NC}"
if [ ! -d ".git" ]; then
    git clone https://github.com/Luolong0223/iot-data-platform.git .
else
    git pull origin main
fi

# 创建 Python 虚拟环境
echo -e "${GREEN}[4/6] 创建 Python 虚拟环境...${NC}"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# 配置环境变量
echo -e "${GREEN}[5/6] 配置环境变量...${NC}"
cat > .env << EOF
FLASK_ENV=production
FLASK_DEBUG=0
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=mysql+pymysql://iot-platform:cRwLGPScNejLEeBt@localhost:3306/iot-platform?charset=utf8mb4
REDIS_URL=redis://localhost:6379/0
EOF

# 创建 MySQL 数据库
echo -e "${GREEN}[6/6] 创建 MySQL 数据库...${NC}"
mysql -u root -p << EOF
CREATE DATABASE IF NOT EXISTS \`iot-platform\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'iot-platform'@'localhost' IDENTIFIED BY 'cRwLGPScNejLEeBt';
GRANT ALL PRIVILEGES ON \`iot-platform\`.* TO 'iot-platform'@'localhost';
FLUSH PRIVILEGES;
EOF

# 初始化数据库
echo "初始化数据库..."
source venv/bin/activate
python -c "from app import create_app; from models.database import db; app = create_app(); app.app_context().push(); db.create_all(); print('Database initialized')"

# 创建 systemd 服务
echo "创建 systemd 服务..."
cat > /etc/systemd/system/iot-platform.service << EOF
[Unit]
Description=IoT Data Platform
After=network.target mysql.service redis.service

[Service]
Type=simple
User=www
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=${PROJECT_DIR}/venv/bin"
ExecStart=${PROJECT_DIR}/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 --timeout 120 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
systemctl daemon-reload
systemctl enable iot-platform
systemctl start iot-platform

# 配置 Nginx
echo "配置 Nginx..."
cat > /www/server/panel/vhost/nginx/iot-platform.conf << EOF
server {
    listen 80;
    server_name iot.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }

    location /static/ {
        alias ${PROJECT_DIR}/static/;
        expires 30d;
    }
}
EOF

# 重载 Nginx
nginx -t && nginx -s reload

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "访问地址: http://iot.your-domain.com"
echo -e "默认账号: admin"
echo -e "默认密码: admin123"
echo -e ""
echo -e "${YELLOW}请修改以下配置:${NC}"
echo -e "1. 修改 Nginx 配置中的 server_name 为你的域名"
echo -e "2. 修改 .env 文件中的 SECRET_KEY"
echo -e "3. 修改数据库密码"
echo -e ""
echo -e "服务管理命令:"
echo -e "  systemctl status iot-platform"
echo -e "  systemctl restart iot-platform"
echo -e "  systemctl stop iot-platform"
