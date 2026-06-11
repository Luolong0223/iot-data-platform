# API 接口文档

本文档详细描述 IoT 数据可视化平台的所有 API 接口，包括请求方法、URL、参数、响应格式及示例。

## 目录

- [接口概览](#接口概览)
- [认证机制](#认证机制)
- [认证路由](#认证路由)
- [管理员路由](#管理员路由)
- [设备路由](#设备路由)
- [数据路由](#数据路由)
- [TCP 配置路由](#tcp-配置路由)
- [错误码说明](#错误码说明)
- [TCP 数据格式规范](#tcp-数据格式规范)

---

## 接口概览

| 模块 | 基础路径 | 说明 |
|------|----------|------|
| 认证 | `/api/auth` | 登录、登出、获取当前用户信息 |
| 管理员 | `/api/admin` | 用户管理、TCP 服务器状态（需管理员权限） |
| 设备 | `/api/devices` | 设备的增删改查与位置设置 |
| 数据 | `/api/data` | 最新数据、历史数据、图表数据、文件上传 |
| TCP 配置 | `/api/tcp` | 获取与更新 TCP 配置 |

**基础 URL**：`http://your-domain/api`

**数据格式**：所有请求与响应均使用 `JSON` 格式，编码为 `UTF-8`。

---

## 认证机制

平台使用基于 **Session** 的认证机制，由 Flask-Login 提供支持。

### 登录流程

1. 客户端调用 `POST /api/auth/login` 提交用户名和密码
2. 服务端验证通过后，在 Cookie 中设置 Session ID
3. 后续请求自动携带 Cookie，服务端通过 Session 识别用户身份

### 请求头要求

对于所有需要认证的接口，请确保请求携带 Cookie。使用浏览器或 HTTP 客户端时，通常会自动处理。

如果使用 AJAX 请求，请设置：

```javascript
fetch('/api/devices', {
  credentials: 'same-origin'  // 确保发送 Cookie
});
```

### 权限说明

| 角色 | 标识 | 权限 |
|------|------|------|
| 管理员 | `is_admin: true` | 可访问所有接口，包括管理员专属接口 |
| 普通用户 | `is_admin: false` | 可访问设备、数据、TCP 配置等接口，只能操作自己的数据 |

---

## 认证路由

### 1. 用户登录

**请求**

```http
POST /api/auth/login
Content-Type: application/json
```

**请求体**

```json
{
  "username": "admin",
  "password": "admin123"
}
```

**响应成功（200 OK）**

```json
{
  "success": true,
  "message": "登录成功",
  "user": {
    "id": 1,
    "username": "admin",
    "is_admin": true,
    "tcp_port": 9000,
    "storage_enabled": true
  }
}
```

**响应失败（401 Unauthorized）**

```json
{
  "success": false,
  "message": "用户名或密码错误"
}
```

---

### 2. 用户登出

**请求**

```http
POST /api/auth/logout
```

**响应成功（200 OK）**

```json
{
  "success": true,
  "message": "登出成功"
}
```

---

### 3. 获取当前用户信息

**请求**

```http
GET /api/auth/me
```

**响应成功（200 OK，已登录）**

```json
{
  "success": true,
  "user": {
    "id": 1,
    "username": "admin",
    "is_admin": true,
    "tcp_port": 9000,
    "storage_enabled": true,
    "created_at": "2024-01-01T08:00:00"
  }
}
```

**响应失败（401 Unauthorized，未登录）**

```json
{
  "success": false,
  "message": "未登录"
}
```

---

## 管理员路由

> **注意**：以下所有接口需要管理员权限（`is_admin: true`），普通用户访问将返回 `403 Forbidden`。

### 4. 获取用户列表

**请求**

```http
GET /api/admin/users
```

**响应成功（200 OK）**

```json
{
  "success": true,
  "users": [
    {
      "id": 1,
      "username": "admin",
      "is_admin": true,
      "tcp_port": 9000,
      "storage_enabled": true,
      "created_at": "2024-01-01T08:00:00"
    },
    {
      "id": 2,
      "username": "user01",
      "is_admin": false,
      "tcp_port": 9001,
      "storage_enabled": true,
      "created_at": "2024-01-02T10:30:00"
    }
  ]
}
```

---

### 5. 添加用户

**请求**

```http
POST /api/admin/users
Content-Type: application/json
```

**请求体**

```json
{
  "username": "user02",
  "password": "user123456",
  "is_admin": false,
  "tcp_port": 9002,
  "storage_enabled": true
}
```

**响应成功（201 Created）**

```json
{
  "success": true,
  "message": "用户创建成功",
  "user": {
    "id": 3,
    "username": "user02",
    "is_admin": false,
    "tcp_port": 9002,
    "storage_enabled": true,
    "created_at": "2024-01-03T14:00:00"
  }
}
```

**响应失败（400 Bad Request，用户名已存在）**

```json
{
  "success": false,
  "message": "用户名已存在"
}
```

---

### 6. 修改用户

**请求**

```http
PUT /api/admin/users/{id}
Content-Type: application/json
```

**URL 参数**：`id` - 用户 ID

**请求体**

```json
{
  "username": "user02_new",
  "password": "newpassword123",
  "is_admin": false,
  "tcp_port": 9002,
  "storage_enabled": true
}
```

> **注意**：`password` 字段为可选，如果不传则不修改密码。

**响应成功（200 OK）**

```json
{
  "success": true,
  "message": "用户更新成功",
  "user": {
    "id": 3,
    "username": "user02_new",
    "is_admin": false,
    "tcp_port": 9002,
    "storage_enabled": true,
    "created_at": "2024-01-03T14:00:00"
  }
}
```

**响应失败（404 Not Found）**

```json
{
  "success": false,
  "message": "用户不存在"
}
```

---

### 7. 删除用户

**请求**

```http
DELETE /api/admin/users/{id}
```

**URL 参数**：`id` - 用户 ID

**响应成功（200 OK）**

```json
{
  "success": true,
  "message": "用户删除成功"
}
```

**响应失败（400 Bad Request，不能删除自己）**

```json
{
  "success": false,
  "message": "不能删除当前登录用户"
}
```

---

### 8. 获取 TCP 服务器状态

**请求**

```http
GET /api/admin/tcp-status
```

**响应成功（200 OK）**

```json
{
  "success": true,
  "tcp_status": {
    "running": true,
    "host": "0.0.0.0",
    "base_port": 9000,
    "active_connections": 12,
    "total_received": 15432,
    "user_ports": [
      {
        "user_id": 1,
        "username": "admin",
        "port": 9000,
        "active": true
      },
      {
        "user_id": 2,
        "username": "user01",
        "port": 9001,
        "active": true
      }
    ]
  }
}
```

---

## 设备路由

### 9. 获取设备列表

**请求**

```http
GET /api/devices
```

**响应成功（200 OK）**

```json
{
  "success": true,
  "devices": [
    {
      "id": 1,
      "name": "Collector-1",
      "voltage_mv": 3037,
      "latitude": 26.5933,
      "longitude": 106.7135,
      "location_name": "贵阳市观山湖区",
      "created_at": "2024-01-01T08:00:00",
      "channels": [
        {
          "id": 1,
          "name": "Slave-1",
          "online": true
        },
        {
          "id": 2,
          "name": "Slave-2",
          "online": true
        }
      ]
    }
  ]
}
```

---

### 10. 添加设备

**请求**

```http
POST /api/devices
Content-Type: application/json
```

**请求体**

```json
{
  "name": "Collector-2",
  "voltage_mv": 4200,
  "latitude": 26.6000,
  "longitude": 106.7200,
  "location_name": "贵阳市南明区"
}
```

**响应成功（201 Created）**

```json
{
  "success": true,
  "message": "设备添加成功",
  "device": {
    "id": 2,
    "name": "Collector-2",
    "voltage_mv": 4200,
    "latitude": 26.6000,
    "longitude": 106.7200,
    "location_name": "贵阳市南明区",
    "created_at": "2024-01-03T15:00:00"
  }
}
```

---

### 11. 修改设备

**请求**

```http
PUT /api/devices/{id}
Content-Type: application/json
```

**URL 参数**：`id` - 设备 ID

**请求体**

```json
{
  "name": "Collector-2-Updated",
  "voltage_mv": 4100,
  "latitude": 26.6100,
  "longitude": 106.7300,
  "location_name": "贵阳市云岩区"
}
```

**响应成功（200 OK）**

```json
{
  "success": true,
  "message": "设备更新成功",
  "device": {
    "id": 2,
    "name": "Collector-2-Updated",
    "voltage_mv": 4100,
    "latitude": 26.6100,
    "longitude": 106.7300,
    "location_name": "贵阳市云岩区",
    "created_at": "2024-01-03T15:00:00"
  }
}
```

---

### 12. 删除设备

**请求**

```http
DELETE /api/devices/{id}
```

**URL 参数**：`id` - 设备 ID

**响应成功（200 OK）**

```json
{
  "success": true,
  "message": "设备删除成功"
}
```

---

### 13. 设置设备位置

**请求**

```http
POST /api/devices/{id}/location
Content-Type: application/json
```

**URL 参数**：`id` - 设备 ID

**请求体**

```json
{
  "latitude": 26.6500,
  "longitude": 106.7500,
  "location_name": "贵阳市花溪区新位置"
}
```

**响应成功（200 OK）**

```json
{
  "success": true,
  "message": "位置设置成功",
  "device": {
    "id": 1,
    "name": "Collector-1",
    "latitude": 26.6500,
    "longitude": 106.7500,
    "location_name": "贵阳市花溪区新位置"
  }
}
```

---

## 数据路由

### 14. 获取最新数据

**请求**

```http
GET /api/data/latest
```

**查询参数（可选）**

| 参数 | 类型 | 说明 |
|------|------|------|
| `device_id` | Integer | 筛选指定设备的最新数据 |
| `limit` | Integer | 返回条数，默认 50，最大 200 |

**响应成功（200 OK）**

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "device_name": "Collector-1",
      "channel_name": "Slave-1",
      "point_name": "Data-1",
      "value": 0.0000,
      "timestamp": "2024-01-01T12:00:00"
    },
    {
      "id": 2,
      "device_name": "Collector-1",
      "channel_name": "Slave-2",
      "point_name": "P1",
      "value": 0.0000,
      "timestamp": "2024-01-01T12:00:00"
    }
  ]
}
```

---

### 15. 获取历史数据

**请求**

```http
GET /api/data/history
```

**查询参数（可选）**

| 参数 | 类型 | 说明 |
|------|------|------|
| `device_id` | Integer | 筛选指定设备 |
| `channel_id` | Integer | 筛选指定通道 |
| `point_name` | String | 筛选指定数据点名称 |
| `start` | String | 开始时间，格式 `YYYY-MM-DD HH:MM:SS` |
| `end` | String | 结束时间，格式 `YYYY-MM-DD HH:MM:SS` |
| `page` | Integer | 页码，默认 1 |
| `per_page` | Integer | 每页条数，默认 20 |

**响应成功（200 OK）**

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "device_name": "Collector-1",
      "channel_name": "Slave-1",
      "point_name": "Data-1",
      "value": 12.34,
      "timestamp": "2024-01-01T10:00:00"
    },
    {
      "id": 5,
      "device_name": "Collector-1",
      "channel_name": "Slave-1",
      "point_name": "Data-1",
      "value": 12.56,
      "timestamp": "2024-01-01T11:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

---

### 16. 获取图表数据

**请求**

```http
GET /api/data/chart/{channel_id}/{point_name}
```

**URL 参数**：
- `channel_id` - 通道 ID
- `point_name` - 数据点名称

**查询参数（可选）**

| 参数 | 类型 | 说明 |
|------|------|------|
| `hours` | Integer | 查询最近多少小时的数据，默认 24 |

**响应成功（200 OK）**

```json
{
  "success": true,
  "chart_data": {
    "channel_id": 1,
    "point_name": "Data-1",
    "labels": [
      "2024-01-01 10:00",
      "2024-01-01 11:00",
      "2024-01-01 12:00"
    ],
    "values": [12.34, 12.56, 12.78]
  }
}
```

---

### 17. 文件上传导入

**请求**

```http
POST /api/upload
Content-Type: multipart/form-data
```

**请求体**

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | File | 上传的文件，支持 CSV、JSON、Excel 格式 |
| `device_id` | Integer | （可选）指定导入到某个设备下 |

**响应成功（200 OK）**

```json
{
  "success": true,
  "message": "文件导入成功",
  "result": {
    "filename": "data_20240101.csv",
    "rows_imported": 150,
    "errors": 0
  }
}
```

**响应失败（400 Bad Request，格式错误）**

```json
{
  "success": false,
  "message": "不支持的文件格式，请上传 CSV、JSON 或 Excel 文件"
}
```

---

## TCP 配置路由

### 18. 获取 TCP 配置

**请求**

```http
GET /api/tcp/config
```

**响应成功（200 OK）**

```json
{
  "success": true,
  "config": {
    "tcp_host": "0.0.0.0",
    "tcp_base_port": 9000,
    "tcp_buffer_size": 4096,
    "tcp_timeout": 30,
    "user_tcp_port": 9001
  }
}
```

> **说明**：`user_tcp_port` 为当前登录用户分配的独立 TCP 端口。

---

### 19. 更新 TCP 配置

**请求**

```http
PUT /api/tcp/config
Content-Type: application/json
```

**请求体**

```json
{
  "tcp_host": "0.0.0.0",
  "tcp_base_port": 9000,
  "tcp_buffer_size": 4096,
  "tcp_timeout": 30
}
```

> **注意**：普通用户只能查看自己的端口，修改全局 TCP 配置需要管理员权限。

**响应成功（200 OK）**

```json
{
  "success": true,
  "message": "TCP 配置更新成功",
  "config": {
    "tcp_host": "0.0.0.0",
    "tcp_base_port": 9000,
    "tcp_buffer_size": 4096,
    "tcp_timeout": 30
  }
}
```

**响应失败（403 Forbidden）**

```json
{
  "success": false,
  "message": "权限不足，需要管理员权限"
}
```

---

## 错误码说明

| HTTP 状态码 | 错误码/说明 | 场景 |
|-------------|-------------|------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 400 | Bad Request | 请求参数错误、格式不正确 |
| 401 | Unauthorized | 未登录或登录已过期 |
| 403 | Forbidden | 已登录但权限不足（如普通用户访问管理员接口） |
| 404 | Not Found | 请求的资源不存在 |
| 405 | Method Not Allowed | 请求方法不允许（如用 GET 访问 POST 接口） |
| 413 | Payload Too Large | 上传文件超过大小限制（默认 16MB） |
| 500 | Internal Server Error | 服务器内部错误 |

### 通用错误响应格式

```json
{
  "success": false,
  "message": "错误描述信息",
  "error_code": "ERROR_CODE_001"
}
```

---

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

> **提示**：`s1`、`s2` 等通道键可以扩展为 `s3`、`s4` 等更多通道，平台会自动解析并创建对应的通道与数据点。设备首次上报时，系统会自动创建设备、通道和数据点记录。

### TCP 发送示例（Python）

```python
import json
import socket

# 用户独立的 TCP 端口
tcp_port = 9001
host = "服务器IP地址"

data = {
    "device": {
        "name": "Collector-1",
        "voltage_mv": 3037
    },
    "s1": {
        "name": "Slave-1",
        "online": 1,
        "data": {
            "Data-1": 25.6
        }
    }
}

# 发送 JSON 数据（末尾加换行符便于服务器解析）
json_str = json.dumps(data) + "\n"

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((host, tcp_port))
    s.sendall(json_str.encode('utf-8'))
    print("数据发送成功")
```

### TCP 发送示例（Node.js）

```javascript
const net = require('net');

const client = new net.Socket();
const tcpPort = 9001;
const host = '服务器IP地址';

const data = {
  device: {
    name: 'Collector-1',
    voltage_mv: 3037
  },
  s1: {
    name: 'Slave-1',
    online: 1,
    data: {
      'Data-1': 25.6
    }
  }
};

client.connect(tcpPort, host, () => {
  client.write(JSON.stringify(data) + '\n');
  client.end();
});

client.on('data', (data) => {
  console.log('Server response:', data.toString());
  client.destroy();
});
```

---

如有其他问题，请参考项目 [README.md](../README.md) 或 [部署文档](deploy.md)。
