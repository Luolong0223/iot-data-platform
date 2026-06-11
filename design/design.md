# IoT 数据可视化平台 - 架构设计文档

## 项目概述
全栈 IoT 数据管理与可视化平台，支持 TCP 透传 JSON 数据接收、传统文件上传、用户管理、地图展示。

## 技术栈
- **后端**: Python 3.9+ + Flask + SQLAlchemy + Flask-Login + Flask-WTF
- **数据库**: SQLite (开发) / MySQL (生产宝塔部署)
- **TCP服务器**: Python asyncio 异步 TCP 服务器
- **前端**: HTML5 + Bootstrap 5 + Leaflet.js (地图) + Chart.js (图表) + DataTables
- **部署**: Gunicorn + Nginx (宝塔面板)

## 数据库模型

### User (用户表)
- id: Integer PK
- username: String(80) Unique
- password_hash: String(256)
- is_admin: Boolean
- tcp_port: Integer (用户独立TCP接收端口)
- storage_enabled: Boolean (是否存储数据)
- created_at: DateTime

### Device (设备表)
- id: Integer PK
- user_id: Integer FK -> User
- name: String(100) (如 Collector-1)
- voltage_mv: Integer
- latitude: Float (地图纬度)
- longitude: Float (地图经度)
- location_name: String(200) (位置描述)
- created_at: DateTime

### SlaveChannel (通道表)
- id: Integer PK
- device_id: Integer FK -> Device
- name: String(100) (如 Slave-1)
- online: Boolean
- created_at: DateTime

### DataPoint (数据点表)
- id: Integer PK
- channel_id: Integer FK -> SlaveChannel
- name: String(100) (如 Data-1, P1)
- value: Float
- timestamp: DateTime

### TcpLog (TCP原始日志表)
- id: Integer PK
- user_id: Integer FK -> User
- raw_data: Text (原始JSON)
- parsed: Boolean
- error_msg: String(500)
- received_at: DateTime

## API 路由设计

### 认证路由
- POST /api/auth/login - 登录
- POST /api/auth/logout - 登出
- GET /api/auth/me - 获取当前用户信息

### 管理员路由
- GET /api/admin/users - 用户列表
- POST /api/admin/users - 添加用户
- PUT /api/admin/users/<id> - 修改用户
- DELETE /api/admin/users/<id> - 删除用户
- GET /api/admin/tcp-status - TCP服务器状态

### 设备路由
- GET /api/devices - 设备列表
- POST /api/devices - 添加设备
- PUT /api/devices/<id> - 修改设备
- DELETE /api/devices/<id> - 删除设备
- POST /api/devices/<id>/location - 设置设备位置

### 数据路由
- GET /api/data/latest - 最新数据
- GET /api/data/history - 历史数据
- GET /api/data/chart/<channel_id>/<point_name> - 图表数据
- POST /api/upload - 文件上传导入

### TCP配置路由
- GET /api/tcp/config - 获取TCP配置
- PUT /api/tcp/config - 更新TCP配置

## 页面路由

### 公共页面
- / - 首页/登录页
- /login - 登录

### 用户页面
- /dashboard - 用户仪表盘
- /devices - 设备管理
- /data - 数据查看
- /map - 地图展示
- /profile - 个人设置

### 管理员页面
- /admin - 管理后台
- /admin/users - 用户管理
- /admin/tcp - TCP服务器管理
- /admin/system - 系统设置

## TCP 数据格式
```json
{
  "device": {
    "name": "Collector-1",
    "voltage_mv": 3037
  },
  "s1": {
    "name": "Slave-1",
    "online": 1,
    "data": {
      "Data-1": 0.0000
    }
  },
  "s2": {
    "name": "Slave-2",
    "online": 1,
    "data": {
      "P1": 0.0000
    }
  }
}
```

## 部署架构 (宝塔面板)
1. 安装 Python 3.9+ 环境
2. 创建网站目录，上传代码
3. 安装依赖: pip install -r requirements.txt
4. 配置 Gunicorn 启动 (端口 5000)
5. Nginx 反向代理
6. 配置 Supervisor 守护 TCP 服务器进程
7. 开放防火墙端口 (TCP 数据端口范围)

## 目录结构
```
iot-data-platform/
├── app.py                 # Flask 主应用入口
├── tcp_server.py          # TCP 透传服务器
├── config.py              # 配置文件
├── requirements.txt       # Python 依赖
├── run.py                 # 启动脚本
├── wsgi.py                # WSGI 入口
├── models/
│   ├── __init__.py
│   └── database.py        # 数据库模型
├── routes/
│   ├── __init__.py
│   ├── auth.py            # 认证路由
│   ├── admin.py           # 管理员路由
│   ├── devices.py         # 设备路由
│   ├── data.py            # 数据路由
│   └── tcp.py             # TCP配置路由
├── services/
│   ├── __init__.py
│   ├── tcp_handler.py     # TCP数据处理
│   └── data_parser.py     # JSON数据解析
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── main.js
│   │   ├── map.js
│   │   ├── chart.js
│   │   └── admin.js
│   └── images/
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── devices.html
│   ├── data_view.html
│   ├── map.html
│   ├── admin/
│   │   ├── base_admin.html
│   │   ├── users.html
│   │   ├── tcp_manage.html
│   │   └── system.html
│   └── errors/
│       ├── 404.html
│       └── 500.html
└── docs/
    ├── deploy.md          # 部署文档
    └── api.md             # API文档
```
