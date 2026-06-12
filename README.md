# IoT 数据可视化平台

一个功能完善的全栈 IoT 数据管理与可视化平台，支持 TCP 透传 JSON 数据接收、设备分组管理、数据导出、报警系统等功能。

## ✨ 功能特性

### 核心功能
- **TCP 透传数据接收**：为每个用户分配独立 TCP 端口，支持异步高并发 JSON 数据接收
- **设备管理**：支持多设备、多通道（Slave）管理，实时显示设备电压与在线状态
- **设备分组**：支持设备分组管理，便于分类查看和批量操作
- **数据可视化**：基于 Chart.js 的实时图表与历史数据趋势分析
- **地图展示**：基于 Leaflet.js 的地理信息展示，支持设备位置标注与追踪
- **数据导出**：支持 Excel、CSV 格式导出历史数据、设备列表、报警记录
- **报警系统**：灵活的报警规则配置，支持多条件判断
- **实时推送**：基于 SSE（Server-Sent Events）的实时数据推送

### 用户与安全
- **用户权限管理**：管理员与普通用户双角色体系，支持独立 TCP 端口分配
- **登录日志审计**：记录所有登录行为，支持安全分析
- **API 限流保护**：防止恶意请求和系统过载
- **密码安全**：支持密码强度校验和账户锁定机制

### 系统监控
- **健康检查接口**：提供系统健康状态监控
- **性能指标**：CPU、内存、磁盘使用情况监控
- **统计报表**：设备数量、数据量、报警数等关键指标

### 前端特性
- **响应式设计**：基于 Bootstrap 5，适配桌面与移动端
- **暗黑模式**：完善的暗黑模式支持
- **现代 UI**：流畅动画、卡片设计、状态指示器

## 🛠 技术栈

| 层级 | 技术 |
|---|---|
| 后端 | Python 3.9+、Flask、SQLAlchemy、Flask-Login、Flask-WTF、Flask-Limiter |
| 数据库 | SQLite（开发环境）/ MySQL（生产环境） |
| TCP 服务器 | Python asyncio 异步 TCP 服务器 |
| 前端 | HTML5、Bootstrap 5、Leaflet.js、Chart.js、DataTables |
| 部署 | Gunicorn + Nginx（宝塔面板） |

## 📁 目录结构

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
│   ├── tcp.py             # TCP 配置路由
│   ├── alarms.py          # 报警路由
│   ├── health.py          # 健康检查路由
│   ├── export.py          # 数据导出路由
│   └── groups.py          # 设备分组路由
├── services/
│   ├── __init__.py
│   ├── tcp_handler.py     # TCP 数据处理
│   ├── data_parser.py     # JSON 数据解析
│   ├── login_log.py       # 登录日志服务
│   └── data_export.py     # 数据导出服务
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
│   ├── alarms.html
│   └── admin/
│       ├── base_admin.html
│       ├── users.html
│       ├── tcp_manage.html
│       └── system.html
├── docs/
│   ├── deploy.md          # 部署文档
│   └── api.md             # API 文档
└── design/
    └── design.md          # 架构设计文档
```

## 🚀 快速开始

### 环境要求

- Python 3.9 或更高版本
- pip 包管理器
- （可选）MySQL 5.7+ 或 MariaDB 10.3+

### 本地开发环境搭建

1. **克隆项目**

```bash
git clone https://github.com/Luolong0223/iot-data-platform.git
cd iot-data-platform
```

2. **创建虚拟环境**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **初始化数据库**

```bash
python -c "from app import app; from models.database import db; app.app_context().push(); db.create_all()"
```

5. **启动开发服务器**

```bash
# 启动 Flask Web 服务
python run.py

# 或使用 Gunicorn
gunicorn -c gunicorn.conf.py wsgi:app
```

6. **访问应用**

打开浏览器访问 `http://127.0.0.1:5000`，默认管理员账号：

- 用户名：`admin`
- 密码：`admin123`

**注意**：生产环境请务必修改默认管理员密码！

## 📡 TCP 数据格式规范

平台通过 TCP 透传接收 JSON 格式的设备数据。每个用户拥有独立的 TCP 接收端口，数据格式如下：

### 基本结构

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

### 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `device.name` | String | 设备名称 |
| `device.voltage_mv` | Integer | 设备电压，单位毫伏（mV） |
| `s1.name` | String | 通道 1 名称 |
| `s1.online` | Integer(0/1) | 通道 1 在线状态 |
| `s1.data` | Object | 通道 1 的数据点集合 |

## 🔌 API 接口

### 健康检查
- `GET /api/health` - 基础健康检查
- `GET /api/health/detailed` - 详细健康检查
- `GET /api/health/metrics` - 系统指标
- `GET /api/health/ready` - 就绪探针
- `GET /api/health/live` - 存活探针

### 数据导出
- `GET /api/export/data/csv` - 导出数据点（CSV）
- `GET /api/export/data/excel` - 导出数据点（Excel）
- `GET /api/export/devices/excel` - 导出设备列表
- `GET /api/export/alarms/excel` - 导出报警记录

### 设备分组
- `GET /api/groups` - 获取分组列表
- `POST /api/groups` - 创建分组
- `PUT /api/groups/<id>` - 更新分组
- `DELETE /api/groups/<id>` - 删除分组
- `POST /api/groups/<id>/devices` - 添加设备到分组

### 认证
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/logout` - 用户登出
- `GET /api/auth/me` - 获取当前用户信息
- `PUT /api/auth/me` - 更新用户信息
- `GET /api/auth/login-history` - 登录历史

## 📊 数据库模型

### 新增模型（v3.0）

- **DeviceGroup**：设备分组表，支持分组颜色、排序
- **LoginLog**：登录日志表，记录登录类型、IP、User-Agent
- **SystemConfig**：系统配置表，键值对存储

### 优化改进

- 为关键字段添加了数据库索引
- 添加了设备在线状态字段（`is_online`, `last_seen_at`）
- 添加了通道最后数据时间字段（`last_data_at`）

## 📝 更新日志

### v3.0 (优化版本)

**新增功能**
- ✅ 数据导出功能（Excel/CSV）
- ✅ 设备分组管理
- ✅ 登录日志审计
- ✅ 系统健康检查接口
- ✅ API 限流保护

**性能优化**
- ✅ 数据库索引优化
- ✅ 连接池配置
- ✅ 查询性能优化

**安全增强**
- ✅ 登录失败次数限制
- ✅ 账户锁定机制
- ✅ API 请求频率限制

**UI 改进**
- ✅ 现代化 UI 样式
- ✅ 改进的暗黑模式
- ✅ 更好的移动端适配

### v2.0

- 实时仪表盘
- 报警系统
- 百度地图集成
- SSE 流式推送

### v1.0

- 初始版本
- 基础数据可视化功能

## 📄 相关文档

| 文档 | 路径 |
|---|---|
| 部署指南（宝塔面板） | [docs/deploy.md](docs/deploy.md) |
| API 接口文档 | [docs/api.md](docs/api.md) |
| 架构设计文档 | [design/design.md](design/design.md) |

## 📜 开源协议

本项目基于 MIT 协议开源。

## ⚠️ 安全提示

**生产环境部署时请务必**：
1. 修改默认管理员密码
2. 配置 HTTPS
3. 开启防火墙规则
4. 定期备份数据库
5. 配置合理的 API 限流参数
6. 使用强密码策略

---

**作者**: Luolong0223  
**GitHub**: https://github.com/Luolong0223/iot-data-platform
