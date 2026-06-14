"""
API 文档服务
自动生成 OpenAPI 3.0 规范的 API 文档，提供 Swagger UI 在线浏览与测试
"""
import os
import re
from pathlib import Path
from flask import Blueprint, jsonify, render_template, send_from_directory, current_app

docs_bp = Blueprint('docs', __name__, url_prefix='/api/docs')

# ============================================================
# OpenAPI 3.0 规范
# ============================================================

def _scan_routes():
    """扫描 Flask 路由，自动提取所有 API 端点"""
    api_rules = []
    for rule in current_app.url_map.iter_rules():
        if not rule.rule.startswith('/api/'):
            continue
        methods = sorted([m for m in rule.methods if m not in ('HEAD', 'OPTIONS')])
        if not methods:
            continue
        # 跳过 Swagger 自身路由
        if rule.rule.startswith('/api/docs'):
            continue
        api_rules.append({
            'path': rule.rule,
            'methods': methods,
            'endpoint': rule.endpoint,
        })
    return sorted(api_rules, key=lambda x: x['path'])


def _build_openapi_spec():
    """构造完整的 OpenAPI 3.0 规范文档"""
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "IoT 数据平台 API",
            "description": (
                "企业级物联网平台 API 文档\n\n"
                "## 核心能力\n"
                "- 设备管理：CRUD、分组、标签、影子、OTA、指令下发\n"
                "- 数据接入：TCP/HTTP/Modbus 多协议\n"
                "- 实时通信：SSE/WebSocket 数据流\n"
                "- 告警与规则：规则引擎、多渠道通知\n"
                "- 平台管理：审计日志、报表、消息中心\n"
                "- 系统：用户、角色、限流、缓存\n\n"
                "## 认证\n"
                "1. 先调用 `/api/auth/login` 获取 session\n"
                "- 浏览器自动携带 cookie\n"
                "- Swagger UI 顶部 Authorize 输入 username/password 即可登录"
            ),
            "version": "4.0.0",
            "contact": {"name": "IoT Platform", "url": "https://github.com/Luolong0223/iot-data-platform"},
            "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"}
        },
        "servers": [
            {"url": "/", "description": "当前服务"},
        ],
        "tags": [
            {"name": "认证", "description": "登录、登出、用户信息"},
            {"name": "设备", "description": "设备 CRUD、详情、统计、历史"},
            {"name": "通道", "description": "通道/数据点管理"},
            {"name": "数据", "description": "数据查询、导出"},
            {"name": "实时", "description": "实时数据流 SSE"},
            {"name": "告警", "description": "告警记录、统计、规则"},
            {"name": "规则引擎", "description": "告警规则 CRUD"},
            {"name": "通知", "description": "通知配置与日志"},
            {"name": "项目", "description": "项目/分组层级管理"},
            {"name": "平台", "description": "设备影子、标签、指令、协议"},
            {"name": "统计", "description": "仪表盘统计"},
            {"name": "TCP", "description": "TCP 服务器状态"},
            {"name": "健康检查", "description": "服务健康状态"},
            {"name": "大屏", "description": "大屏数据点选择"},
            {"name": "导出", "description": "数据导出 Excel/CSV"},
        ],
        "components": {
            "securitySchemes": {
                "cookieAuth": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "session",
                    "description": "Flask-Login session cookie"
                }
            },
            "schemas": {
                "Success": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": True},
                        "data": {"type": "object"},
                        "message": {"type": "string"}
                    }
                },
                "Error": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": False},
                        "error": {"type": "string"},
                        "code": {"type": "integer"}
                    }
                },
                "Device": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string", "example": "Collector-1"},
                        "device_type": {"type": "string", "example": "collector"},
                        "device_key": {"type": "string"},
                        "voltage_mv": {"type": "integer", "example": 3037},
                        "latitude": {"type": "number", "format": "float"},
                        "longitude": {"type": "number", "format": "float"},
                        "location_name": {"type": "string"},
                        "is_online": {"type": "boolean"},
                        "storage_enabled": {"type": "boolean"},
                        "last_seen_at": {"type": "string", "format": "date-time"},
                    }
                },
                "AlarmRule": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "device_id": {"type": "integer"},
                        "data_point": {"type": "string", "example": "temperature"},
                        "operator": {"type": "string", "enum": [">", "<", ">=", "<=", "==", "!="]},
                        "threshold": {"type": "number"},
                        "severity": {"type": "string", "enum": ["info", "warning", "error", "critical"]},
                        "is_enabled": {"type": "boolean"},
                        "cooldown": {"type": "integer", "description": "冷却时间（秒）"}
                    }
                },
                "Project": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "user_id": {"type": "integer"}
                    }
                },
                "DeviceShadow": {
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "integer"},
                        "reported_state": {"type": "object", "description": "设备上报状态"},
                        "desired_state": {"type": "object", "description": "期望状态"},
                        "version": {"type": "integer"},
                        "updated_at": {"type": "string", "format": "date-time"}
                    }
                }
            }
        },
        "security": [{"cookieAuth": []}],
        "paths": _build_paths()
    }


def _build_paths():
    """根据 Flask 路由自动生成 OpenAPI paths"""
    paths = {}
    tag_map = _infer_tag_map()

    for rule in current_app.url_map.iter_rules():
        if not rule.rule.startswith('/api/'):
            continue
        if rule.rule.startswith('/api/docs'):
            continue

        path = rule.rule
        # Flask 路径参数 <id> -> OpenAPI {id}
        openapi_path = re.sub(r'<(\w+)>', r'{\1}', path)

        methods = sorted([m for m in rule.methods if m not in ('HEAD', 'OPTIONS')])
        if not methods:
            continue

        path_item = paths.setdefault(openapi_path, {})
        for method in methods:
            operation = _build_operation(rule.endpoint, method, path, tag_map)
            path_item[method.lower()] = operation

    return paths


def _infer_tag_map():
    """根据 URL 前缀推断 tag 分类"""
    return {
        'auth': '认证',
        'devices': '设备',
        'channels': '通道',
        'data': '数据',
        'realtime': '实时',
        'alarms': '告警',
        'alarm_rules': '规则引擎',
        'notifications': '通知',
        'projects': '项目',
        'platform': '平台',
        'dashboard': '统计',
        'tcp': 'TCP',
        'health': '健康检查',
        'screen': '大屏',
        'export': '导出',
    }


def _build_operation(endpoint_name, method, path, tag_map):
    """构造单个 OpenAPI operation 对象"""
    # 推断 tag
    tag = '其他'
    for prefix, t in tag_map.items():
        if prefix in endpoint_name.lower() or prefix in path.lower():
            tag = t
            break

    op = {
        "tags": [tag],
        "summary": _infer_summary(endpoint_name, method, path),
        "description": _infer_description(endpoint_name, method),
        "operationId": f"{method.lower()}_{endpoint_name.replace('.', '_')}",
        "responses": _infer_responses(method)
    }

    # 请求体
    if method in ('POST', 'PUT', 'PATCH'):
        op["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"type": "object", "additionalProperties": True}
                }
            }
        }

    # 路径参数
    path_params = re.findall(r'<(\w+)>', path)
    if path_params:
        op["parameters"] = [
            {
                "name": p, "in": "path", "required": True,
                "schema": {"type": _infer_param_type(p)}
            } for p in path_params
        ]

    # 查询参数（id / page / per_page 等）
    if method == 'GET':
        op.setdefault("parameters", []).extend([
            {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}, "description": "页码"},
            {"name": "per_page", "in": "query", "schema": {"type": "integer", "default": 20}, "description": "每页数量"},
        ])

    return op


def _infer_summary(endpoint, method, path):
    """根据 endpoint 名推断摘要"""
    verb_map = {
        'GET': '获取', 'POST': '创建', 'PUT': '更新', 'PATCH': '修改', 'DELETE': '删除'
    }
    verb = verb_map.get(method, method)
    # 简化 endpoint 名称
    name = endpoint.split('.')[-1].replace('_', ' ')
    return f"{verb} {name}"


def _infer_description(endpoint, method):
    """推断描述"""
    if 'list' in endpoint:
        return "返回分页数据列表"
    if method == 'POST':
        return "创建新资源"
    if method == 'PUT' or method == 'PATCH':
        return "更新资源"
    if method == 'DELETE':
        return "删除资源"
    return ""


def _infer_responses(method):
    """构造标准响应"""
    return {
        "200": {
            "description": "成功",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Success"}
                }
            }
        },
        "400": {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Error"}
                }
            }
        },
        "401": {
            "description": "未登录",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Error"}
                }
            }
        },
        "403": {
            "description": "无权限",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Error"}
                }
            }
        },
        "404": {
            "description": "资源不存在",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Error"}
                }
            }
        },
        "500": {
            "description": "服务器内部错误",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Error"}
                }
            }
        }
    }


def _infer_param_type(name):
    """推断参数类型"""
    if name in ('id', 'device_id', 'channel_id', 'rule_id', 'project_id', 'group_id', 'tag_id', 'command_id', 'shadow_id', 'silence_id'):
        return 'integer'
    return 'string'


# ============================================================
# 路由
# ============================================================

@docs_bp.route('/spec', methods=['GET'])
def get_spec():
    """返回 OpenAPI 3.0 规范 JSON"""
    return jsonify(_build_openapi_spec())


@docs_bp.route('/', methods=['GET'])
@docs_bp.route('/ui', methods=['GET'])
def swagger_ui():
    """Swagger UI 页面"""
    return render_template('swagger.html')


@docs_bp.route('/redoc', methods=['GET'])
def redoc_ui():
    """ReDoc 文档页面"""
    return render_template('redoc.html')


@docs_bp.route('/endpoints', methods=['GET'])
def list_endpoints():
    """列出所有 API 端点（调试用）"""
    return jsonify({
        'success': True,
        'count': len(_scan_routes()),
        'endpoints': _scan_routes()
    })


@docs_bp.route('/postman', methods=['GET'])
def postman_collection():
    """导出 Postman Collection 格式"""
    spec = _build_openapi_spec()
    collection = {
        "info": {
            "name": spec['info']['title'],
            "description": spec['info']['description'],
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "item": [],
        "auth": {
            "type": "cookie",
            "cookie": [{"key": "session", "value": "{{session}}", "type": "string"}]
        },
        "variable": [
            {"key": "baseUrl", "value": "/", "type": "string"},
            {"key": "session", "value": "", "type": "string"}
        ]
    }
    for path, methods in spec['paths'].items():
        for method, op in methods.items():
            item = {
                "name": op.get('summary', f"{method.upper()} {path}"),
                "request": {
                    "method": method.upper(),
                    "header": [{"key": "Content-Type", "value": "application/json"}],
                    "url": {
                        "raw": "{{baseUrl}}" + path,
                        "host": ["{{baseUrl}}"],
                        "path": path.strip('/').split('/')
                    }
                }
            }
            if 'requestBody' in op:
                item['request']['body'] = {
                    "mode": "raw",
                    "raw": "{}"
                }
            collection['item'].append(item)
    return jsonify(collection)
