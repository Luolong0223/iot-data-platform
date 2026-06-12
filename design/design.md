# IoT 数据可视化平台 - 架构设计文档 v3.0

## 项目概述
全栈 IoT 数据管理与可视化平台，支持 TCP 透传 JSON 数据接收、设备分组管理、数据导出、报警系统等功能。

## 技术栈
- **后端**: Python 3.9+ + Flask + SQLAlchemy + Flask-Login + Flask-WTF + Flask-Limiter
- **数据库**: SQLite (开发) / MySQL (生产宝塔部署)
- **TCP服务器**: Python asyncio 异步 TCP 服务器
- **前端**: HTML5 + Bootstrap 5 + Leaflet.js (地图) + Chart.js (图表) + DataTables
- **部署**: Gunicorn + Nginx (宝塔面板)

## 数据库模型

### User (用户表)
- id: Integer PK
- username: String(80) Unique, 索引
- password_hash: String(256)
- email: String(120) Unique
- is_admin: Boolean
- tcp_port: Integer (用户独立TCP接收端口)
- storage_enabled: Boolean (是否存储数据)
- is_active: Boolean (账户是否激活)
- last_login_at: DateTime (最后登录时间)
- last_login_ip: String(45) (最后登录IP)
- created_at: DateTime

### DeviceGroup (设备分组表) - 新增
- id: Integer PK
- user_id: Integer FK -> User, 索引
- name: String(100)
- description: String(500)
- color: String(7) (分组颜色)
- sort_order: Integer (排序)
- created_at: DateTime

### Device (设备表)
- id: Integer PK
- user_id: Integer FK -> User, 索引
- group_id: Integer FK -> DeviceGroup, 索引
- name: String(100)
- device_type: String(50) (设备类型)
- voltage_mv: Integer
- latitude: Float (地图纬度)
- longitude: Float (地图经度)
- location_name: String(200) (位置描述)
- last_seen_at: DateTime (最后通信时间)
- is_online: Boolean (在线状态)
- created_at: DateTime

### SlaveChannel (通道表)
- id: Integer PK
- device_id: Integer FK -> Device, 索引
- name: String(100)
- online: Boolean
- last_data_at: DateTime (最后数据时间)
- created_at: DateTime

### DataPoint (数据点表)
- id: Integer PK
- channel_id: Integer FK -> SlaveChannel, 索引
- name: String(100), 索引
- value: Float
- timestamp: DateTime, 索引
- 复合索引: (channel_id, name, timestamp)

### TcpLog (TCP原始日志表)
- id: Integer PK
- user_id: Integer FK -> User, 索引
- raw_data: Text (原始JSON)
- parsed: Boolean, 索引
- error_msg: String(500)
- client_ip: String(45)
- received_at: DateTime, 索引

### LoginLog (登录日志表) - 新增
- id: Integer PK
- user_id: Integer FK -> User, 索引
- username: String(80), 索引
- login_type: String(20) (login, logout, failed)
- ip_address: String(45)
- user_agent: String(500)
- success: Boolean
- failure_reason: String(200)
- created_at: DateTime, 索引

### AlarmRule (报警规则表)
- id: Integer PK
- user_id: Integer FK -> User, 索引
- device_name: String(100), 索引
- channel_name: String(100)
- point_name: String(100)
- condition: String(10) (gt, lt, eq, gte, lte)
- threshold: Float
- severity: String(20) (info, warning, critical)
- notify_email: Boolean
- notify_sms: Boolean
- enabled: Boolean, 索引
- created_at: DateTime

### AlarmRecord (报警记录表)
- id: Integer PK
- user_id: Integer FK -> User, 索引
- rule_id: Integer FK -> AlarmRules, 索引
- device_name: String(100), 索引
- channel_name: String(100)
- point_name: String(100)
- value: Float
- threshold: Float
- condition: String(10)
- severity: String(20)
- message: String(500)
- is_read: Boolean, 索引
- is_handled: Boolean
- handled_by: String(80)
- handled_at: DateTime
- created_at: DateTime, 索引

### SystemConfig (系统配置表) - 新增
- id: Integer PK
- key: String(100) Unique, 索引
- value: Text
- description: String(500)
- updated_at: DateTime

## API 路由设计

### 认证路由 (/api/auth)
- POST /login - 登录（含限流、日志记录）
- POST /logout - 登出
- GET /me - 获取当前用户信息
- PUT /me - 更新用户信息
- GET /login-history - 登录历史
- POST /check-username - 检查用户名可用性

### 管理员路由 (/api/admin)
- GET /users - 用户列表
- POST /users - 添加用户
- PUT /users/<id> - 修改用户
- DELETE /users/<id> - 删除用户
- GET /tcp-status - TCP服务器状态

### 设备路由 (/api/devices)
- GET / - 设备列表
- POST / - 添加设备
- PUT /<id> - 修改设备
- DELETE /<id> - 删除设备
- POST /<id>/location - 设置设备位置

### 设备分组路由 (/api/groups) - 新增
- GET / - 分组列表
- POST / - 创建分组
- PUT /<id> - 更新分组
- DELETE /<id> - 删除分组
- GET /<id>/devices - 获取分组内设备
- POST /<id>/devices - 添加设备到分组
- DELETE /<id>/devices/<device_id> - 移除设备
- POST /reorder - 重新排序

### 数据路由 (/api/data)
- GET /latest - 最新数据
- GET /history - 历史数据
- GET /chart/<channel_id>/<point_name> - 图表数据
- POST /upload - 文件上传导入

### 数据导出路由 (/api/export) - 新增
- GET /data/csv - 导出数据点（CSV）
- GET /data/excel - 导出数据点（Excel）
- GET /devices/excel - 导出设备列表
- GET /alarms/excel - 导出报警记录

### 健康检查路由 (/api/health) - 新增
- GET / - 基础健康检查
- GET /detailed - 详细健康检查
- GET /metrics - 系统指标
- GET /ready - 就绪探针
- GET /live - 存活探针

### 报警路由 (/api/alarms)
- GET /rules - 报警规则列表
- POST /rules - 创建报警规则
- PUT /rules/<id> - 更新报警规则
- DELETE /rules/<id> - 删除报警规则
- GET /records - 报警记录列表
- PUT /records/<id>/read - 标记已读

### 流式推送路由 (/api/stream)
- GET /events - SSE实时数据推送

## 性能优化

### 数据库优化
- 关键字段添加索引
- 复合索引优化查询
- 连接池配置
- 查询优化避免N+1问题

### 缓存策略
- 可选Redis缓存热点数据
- 会话存储可迁移到Redis
- 统计数据缓存

### 前端优化
- 静态资源压缩
- 图表组件懒加载
- 虚拟滚动（大数据列表）

## 安全设计

### 认证安全
- 登录失败次数限制
- 账户锁定机制
- 登录日志审计
- 密码强度校验

### API安全
- 请求频率限制
- CSRF保护
- XSS防护
- SQL注入防护（ORM）

### 数据安全
- 密码加密存储
- 敏感信息脱敏
- 操作日志记录

## 部署架构

### 开发环境
```
Flask Dev Server (Port 5000)
    |
    +-- TCP Server (Port 9105+)
    |
    +-- SQLite Database
```

### 生产环境
```
Nginx (Port 80/443)
    |
    +-- Gunicorn (Port 5000)
    |       |
    |       +-- Flask App
    |       |       |
    |       |       +-- TCP Server (后台线程)
    |       |       |
    |       |       +-- MySQL Database
    |       |
    |       +-- Workers (4+)
    |
    +-- SSL Termination
    |
    +-- Static Files
```

## 扩展性设计

### 横向扩展
- TCP服务器可独立部署
- 应用服务器无状态设计
- 数据库读写分离

### 功能扩展
- 模块化蓝图设计
- 插件化报警通知
- 自定义数据解析器

## 监控告警

### 应用监控
- 健康检查接口
- 性能指标采集
- 错误日志收集

### 业务监控
- 设备在线率
- 数据接收量
- 报警触发统计
