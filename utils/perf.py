"""
性能优化工具
- 分页助手（统一 page/size/返回 total/items/page_meta）
- 字段过滤（仅返回指定字段）
- 简单查询计时（仅开发环境）
"""
from functools import wraps
from flask import request, jsonify, current_app
from sqlalchemy import inspect
import time


def paginate(query, default_size: int = 20, max_size: int = 200):
    """
    从 query 构造分页结果。
    使用 request.args 中的 page/size，返回 (items, meta)
    """
    try:
        page = max(1, int(request.args.get('page', 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        size = int(request.args.get('size', default_size))
    except (ValueError, TypeError):
        size = default_size
    size = min(max(1, size), max_size)

    total = query.count()
    items = query.limit(size).offset((page - 1) * size).all()
    pages = (total + size - 1) // size if size else 1
    return items, {
        'page': page,
        'size': size,
        'total': total,
        'pages': pages,
        'has_next': page < pages,
        'has_prev': page > 1,
    }


def paginated_response(query, serializer=None, default_size: int = 20):
    """直接返回分页 JSON 响应"""
    items, meta = paginate(query, default_size=default_size)
    if serializer is None:
        # 尝试 .to_dict()
        data = [i.to_dict() if hasattr(i, 'to_dict') else i for i in items]
    else:
        data = [serializer(i) for i in items]
    return jsonify({'success': True, 'data': data, 'meta': meta})


def time_query(f):
    """装饰器：记录查询耗时（仅开发模式）"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_app.debug:
            return f(*args, **kwargs)
        t0 = time.perf_counter()
        result = f(*args, **kwargs)
        dt = (time.perf_counter() - t0) * 1000
        current_app.logger.info(f'[PERF] {f.__name__}: {dt:.1f}ms')
        return result
    return wrapper


# 常用字段白名单
DEFAULT_DEVICE_FIELDS = [
    'id', 'name', 'voltage_mv', 'tcp_port', 'is_active', 'created_at'
]


def project_fields(obj, fields: list = None):
    """提取对象指定字段"""
    if fields is None:
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
    if not fields:
        return obj.to_dict() if hasattr(obj, 'to_dict') else {}
    out = {}
    for f in fields:
        v = getattr(obj, f, None)
        if hasattr(v, 'isoformat'):
            v = v.isoformat()
        elif hasattr(v, 'value'):  # Enum
            v = v.value
        out[f] = v
    return out
