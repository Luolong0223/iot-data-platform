# AGENTS.md - IoT Data Platform

## 项目概览
基于 Flask 的物联网数据可视化平台，支持 TCP 透传接收 JSON 设备数据，提供用户/管理员登录、设备管理、地图、告警、数据大屏等能力。

## 技术栈
- **后端**: Python 3.9 + Flask 2.3 + SQLAlchemy 2.0
- **数据库**: MySQL（生产）/ SQLite（开发）
- **认证**: Flask-Login
- **限流**: Flask-Limiter
- **邮件**: Flask-Mail
- **实时通信**: SSE (Server-Sent Events)
- **TCP 接入**: 原生 asyncio
- **前端**: Bootstrap 5 + Chart.js + DataTables + Leaflet/百度地图

## 项目结构
```
.
├── app.py                       # 应用工厂
├── run.py                       # 启动入口
├── config.py                    # 配置（DB、邮件、限流等）
├── wsgi.py                      # WSGI 入口
├── init_mysql.py                # MySQL 初始化脚本
├── upgrade_v3.py / upgrade_v4.py # 数据库升级脚本
├── models/
│   └── database.py              # 数据模型 (User/Device/Channel/DataPoint/Alarm/Project等)
├── routes/                      # 路由蓝图
│   ├── auth.py                  # 登录/登出
│   ├── admin.py                 # 管理员后台
│   ├── devices.py               # 设备管理
│   ├── data.py                  # 数据查询
│   ├── alarms.py                # 告警管理
│   ├── alarm_rules.py           # 告警规则
│   ├── dashboard_api.py         # 主控台统计
│   ├── realtime.py              # SSE 实时流
│   ├── screen.py                # 大屏 API（数据点选择、趋势）
│   ├── stream.py                # SSE 流（兼容层）
│   ├── tcp.py                   # TCP 配置
│   ├── projects.py              # 项目管理（v4.0）
│   ├── groups.py                # 设备分组
│   ├── export.py                # 数据导出
│   ├── health.py                # 健康检查
│   └── pages.py                 # 页面路由
├── services/                    # 业务服务层
│   ├── tcp_handler.py           # TCP 数据处理
│   ├── notification.py          # 通知服务（邮件/钉钉/企业微信）
│   ├── data_export.py           # Excel/CSV 导出
│   ├── data_parser.py           # 协议解析
│   └── login_log.py             # 登录审计
├── templates/                   # Jinja2 模板
│   ├── base.html                # 基础布局
│   ├── dashboard.html           # 主控台
│   ├── screen.html              # 数据大屏（含数据点选择器）
│   ├── devices.html             # 设备管理
│   ├── device_detail.html       # 设备详情
│   ├── hierarchy.html           # 设备层级
│   ├── alarm_rules.html         # 告警规则
│   ├── alarms.html              # 告警中心
│   ├── map.html                 # 地图
│   ├── data_view.html           # 数据查看
│   ├── admin/                   # 管理员页面
│   └── errors/                  # 错误页
├── static/                      # 静态资源
│   ├── css/style.css
│   └── js/                      # dashboard.js/screen.js/main.js/data.js/devices.js
└── instance/database.db         # SQLite 数据库（开发）
```

## 数据模型（models/database.py）
- **User**: 用户（管理员/普通用户），含 tcp_port、storage_enabled
- **Project**: 项目（v4.0 层级管理）
- **DeviceGroup**: 设备分组（支持多级嵌套）
- **Device**: 设备（含 project_id、device_key、ip、固件版本、维护周期等）
- **Channel/SlaveChannel**: 通道（设备-从机）
- **DataPoint**: 数据点（name, value, timestamp）
- **AlarmRule**: 告警规则（条件 + 通知）
- **AlarmRecord**: 告警记录
- **NotificationConfig**: 通知渠道配置
- **ScreenSelectedPoint**: 大屏已选数据点（持久化）
- **LoginLog**: 登录日志

## 核心 API
- `/api/auth/login` - 登录
- `/api/devices` - 设备列表/CRUD
- `/api/data/history` - 历史数据
- `/api/alarms/records` - 告警记录
- `/api/alarm-rules` - 告警规则 CRUD
- `/api/dashboard/stats` - 主控台统计
- `/api/dashboard/trend` - 主控台趋势
- `/api/realtime/stream` - SSE 实时流
- `/api/realtime/stats` - 实时统计
- `/api/realtime/trend` - 趋势数据（支持按 channel_id+point_name 查询）
- `/api/screen/data-points` - 大屏数据点选择器
- `/api/screen/saved-points` - 大屏已选数据点 CRUD
- `/api/screen/selected-data` - 大屏已选数据点实时值
- `/api/screen/point-trend` - 单数据点历史趋势
- `/api/projects` - 项目管理
- `/api/groups` - 设备分组
- `/api/export/data` - 数据导出
- `/api/health/live` `/api/health/ready` - 健康检查

## 启动方式
```bash
# 开发
python run.py

# 生产 (gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app

# MySQL 初始化
python init_mysql.py

# 数据库升级 (v3 -> v4)
python upgrade_v4.py
```

## 常见问题排查

### 1. 启动报 "no such column"
运行 `python upgrade_v4.py` 添加缺失字段（项目根目录）

### 2. 设备列表 500
检查 `devices` 表是否含 `storage_enabled`、`ip_address` 等字段。运行 upgrade_v4.py

### 3. 大屏选择器无内容
- 确认已登录（页面调用 API 需 session）
- 确认有设备（TCP 客户端发送数据后会自动创建）
- 检查浏览器控制台报错

### 4. SSE 实时流不刷新
- 浏览器控制台查看 EventSource 连接状态
- TCP 客户端是否在发送数据到分配的端口
- 查看 `tcp_server.log`

## 端口分配
- Web: 5000 (或宝塔配置的端口)
- TCP: 每个用户独立端口（admin=9105, user1=9106...，可在管理后台调整）

## 数据库表结构（MySQL 兼容）
所有表前缀、主键、外键由 SQLAlchemy 自动生成。建议使用 `mysql+pymysql://` 驱动。

## 安全要点
- 密码 Werkzeug 哈希
- Flask-Login Session 认证
- Flask-Limiter API 限流
- 登录失败次数限制
- CSRF 保护（API 路由已豁免）
