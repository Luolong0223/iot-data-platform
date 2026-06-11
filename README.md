# IoT 数据可视化平台

一个全栈 IoT 数据管理与可视化平台，支持 TCP 透传 JSON 数据接收、传统文件上传、用户管理、地图展示等功能。

## 功能特性

- **TCP 透传数据接收**：为每个用户分配独立 TCP 端口，支持异步高并发 JSON 数据接收
- **设备管理**：支持多设备、多通道（Slave）管理，实时显示设备电压与在线状态
- **数据可视化**：基于 Chart.js 的实时图表与历史数据趋势分析
- **地图展示**：基于 Leaflet.js 的地理信息展示，支持设备位置标注与追踪
- **文件上传导入**：支持通过 Web 页面上传数据文件进行批量导入
- **用户权限管理**：管理员与普通用户双角色体系，支持独立 TCP 端口分配
- **响应式前端**：基于 Bootstrap 5 的现代化 UI，适配桌面与移动端

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.9+、Flask、SQLAlchemy、Flask-Login、Flask-WTF |
| 数据库 | SQLite（开发环境）/ MySQL（生产环境） |
| TCP 服务器 | Python asyncio 异步 TCP 服务器 |
| 前端 | HTML5、Bootstrap 5、Leaflet.js、Chart.js、DataTables |
| 部署 | Gunicorn + Nginx（宝塔面板） |

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
│   └── tcp.py             # TCP 配置路由
├── services/
│   ├── __init__.py
│   ├── tcp_handler.py     # TCP 数据处理
│   └── data_parser.py     # JSON 数据解析
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
├── docs/
│   ├── deploy.md          # 部署文档
│   └── api.md             # API 文档
└── design/
    └── design.md          # 架构设计文档
```

## 快速开始

### 环境要求

- Python 3.9 或更高版本
- pip 包管理器
- （可选）MySQL 5.7+ 或 MariaDB 10.3+

### 本地开发环境搭建

1. **克隆项目**

```bash
git clone <repository-url>
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

# 另开一个终端，启动 TCP 服务器
python tcp_server.py
```

6. **访问应用**

打开浏览器访问 `http://127.0.0.1:5000`，默认管理员账号：
- 用户名：`admin`
- 密码：`admin123`

> **注意**：生产环境请务必修改默认管理员密码！

### 生产环境部署

生产环境建议使用 **宝塔面板 + Windows Server 2019** 部署，详细步骤请参考：

📄 [docs/deploy.md](docs/deploy.md)

## TCP 数据格式规范

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
|------|------|------|
| `device.name` | String | 设备名称，如 `Collector-1` |
| `device.voltage_mv` | Integer | 设备电压，单位毫伏（mV） |
| `s1.name` | String | 通道 1 名称，如 `Slave-1` |
| `s1.online` | Integer(0/1) | 通道 1 在线状态，1 为在线，0 为离线 |
| `s1.data` | Object | 通道 1 的数据点集合，键值对形式 |
| `s2.name` | String | 通道 2 名称，如 `Slave-2` |
| `s2.online` | Integer(0/1) | 通道 2 在线状态 |
| `s2.data` | Object | 通道 2 的数据点集合 |

### 示例 1：单设备双通道基础数据

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

### 示例 2：多数据点传感器数据

```json
{
  "device": {
    "name": "Collector-A2",
    "voltage_mv": 4200
  },
  "s1": {
    "name": "TempSensor",
    "online": 1,
    "data": {
      "Temperature": 26.5,
      "Humidity": 68.2,
      "Pressure": 1013.25
    }
  },
  "s2": {
    "name": "PowerMeter",
    "online": 1,
    "data": {
      "Voltage": 220.5,
      "Current": 1.25,
      "Power": 275.6
    }
  }
}
```

### 示例 3：部分通道离线状态

```json
{
  "device": {
    "name": "Collector-B3",
    "voltage_mv": 2800
  },
  "s1": {
    "name": "Slave-1",
    "online": 1,
    "data": {
      "Data-1": 12.34,
      "Data-2": 56.78
    }
  },
  "s2": {
    "name": "Slave-2",
    "online": 0,
    "data": {}
  }
}
```

### 示例 4：单通道环境监测数据

```json
{
  "device": {
    "name": "EnvMonitor-01",
    "voltage_mv": 3600
  },
  "s1": {
    "name": "AirQuality",
    "online": 1,
    "data": {
      "PM2.5": 35.0,
      "PM10": 58.0,
      "CO2": 450.0,
      "TVOC": 0.32
    }
  }
}
```

> **提示**：`s1`、`s2` 等通道键可以扩展为 `s3`、`s4` 等更多通道，平台会自动解析并创建对应的通道与数据点。

## 界面截图说明

平台包含以下主要界面：

| 页面 | 说明 |
|------|------|
| 登录页 (`/login`) | 简洁的登录界面，支持管理员与普通用户登录 |
| 仪表盘 (`/dashboard`) | 数据总览，展示设备数量、在线状态、最新数据等关键指标 |
| 设备管理 (`/devices`) | 设备列表与详情，支持添加、编辑、删除设备，设置设备位置 |
| 数据查看 (`/data`) | 基于 DataTables 的数据列表，支持筛选、排序、分页 |
| 地图展示 (`/map`) | 基于 Leaflet.js 的地理信息可视化，标注设备实时位置 |
| 个人设置 (`/profile`) | 用户个人信息与 TCP 端口配置查看 |
| 管理后台 (`/admin`) | 管理员专属后台，包含用户管理、TCP 服务器管理、系统设置 |

## API 文档

详细的 API 接口文档请参考：

📄 [docs/api.md](docs/api.md)

## 相关文档

| 文档 | 路径 |
|------|------|
| 部署指南（宝塔面板） | [docs/deploy.md](docs/deploy.md) |
| API 接口文档 | [docs/api.md](docs/api.md) |
| 架构设计文档 | [design/design.md](design/design.md) |

## 开源协议

本项目基于 MIT 协议开源。

---

**注意**：本项目为演示与学习用途，生产环境部署时请务必修改默认密码、配置 HTTPS、开启防火墙规则，并定期备份数据库。
