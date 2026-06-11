# IoT 平台 v2.0 功能增强设计

## 1. 实时数据查看 (SSE)
- 后端：Flask SSE 端点 `/api/stream/events`
- 前端：EventSource 连接，仪表盘实时刷新
- 数据推送时机：TCP 接收新数据时广播

## 2. 报警系统
### 模型
- **AlarmRule**：用户ID、设备名、通道名、数据点名、条件(gt/lt/eq)、阈值、启用状态
- **AlarmRecord**：规则ID、实际值、阈值、报警消息、是否已读

### 逻辑
- TCP 接收数据 → store_data → check_alarms → 匹配规则 → 创建 AlarmRecord → SSE 推送

### API
- GET/POST/PUT/DELETE `/api/alarms/rules`
- GET `/api/alarms/records`
- PUT `/api/alarms/records/<id>/read`

## 3. 仪表盘增强
- 实时数据流卡片（最近接收的数据）
- 设备在线/离线统计
- 今日报警数量
- 电压趋势图
- 最近活动时间线

## 4. 百度地图
- 替换 Leaflet.js
- 使用百度地图 JavaScript API v3.0
- 需要配置 BAIDU_MAP_AK
- 设备标记 + 信息窗口

## 文件变更清单
### 后端
- models/database.py：+AlarmRule, +AlarmRecord
- config.py：+BAIDU_MAP_AK
- services/tcp_handler.py：+check_alarms()
- routes/alarms.py：新增
- routes/stream.py：新增
- app.py：注册新蓝图

### 前端
- templates/dashboard.html：重写
- templates/alarms.html：新增
- templates/map.html：百度地图
- static/js/dashboard.js：新增
- static/js/alarms.js：新增
- static/js/map.js：百度地图
- static/css/style.css：+新样式
