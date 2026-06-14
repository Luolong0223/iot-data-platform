"""审计日志服务 - 自动记录用户关键操作"""
from datetime import datetime
from functools import wraps
from flask import request
from flask_login import current_user
from models.database import db, AuditLog


def log_action(action, resource=None, resource_id=None, detail=None, status='success'):
    """记录操作日志（带容错）"""
    try:
        user_id = current_user.id if current_user.is_authenticated else None
        username = current_user.username if current_user.is_authenticated else None
        ip = request.headers.get('X-Forwarded-For', request.remote_addr) if request else None
        ua = request.headers.get('User-Agent', '')[:255] if request else None

        log = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            resource=resource,
            resource_id=str(resource_id) if resource_id else None,
            detail=str(detail)[:2000] if detail else None,
            ip=ip,
            user_agent=ua,
            status=status
        )
        db.session.add(log)
        db.session.commit()
        return log
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        # 日志记录失败不应阻塞主业务
        print(f'[audit_log] 记录失败: {e}')
        return None


def audit(action, resource=None, detail_fn=None):
    """装饰器：自动审计函数调用

    usage:
        @audit('delete', resource='device')
        def delete_device(id):
            ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            detail = None
            status = 'success'
            try:
                if detail_fn:
                    try:
                        detail = detail_fn(*args, **kwargs)
                    except Exception:
                        pass
                result = fn(*args, **kwargs)
                return result
            except Exception as e:
                status = 'failed'
                detail = f'{detail or ""} | error: {str(e)[:500]}'
                raise
            finally:
                log_action(action, resource=resource,
                          resource_id=kwargs.get('id') or kwargs.get('device_id'),
                          detail=detail, status=status)
        return wrapper
    return decorator
