"""
服务工具类 - 简化版登录日志、审计日志
"""
import logging
from datetime import datetime, timedelta
from flask import request
from models.database import db, LoginLog

logger = logging.getLogger(__name__)


class LoginLogService:
    """登录日志服务 - 简化版"""

    @staticmethod
    def get_client_ip():
        """获取客户端真实IP"""
        try:
            if request and request.headers.get('X-Forwarded-For'):
                return request.headers.get('X-Forwarded-For').split(',')[0].strip()
            if request and request.headers.get('X-Real-IP'):
                return request.headers.get('X-Real-IP')
            return request.remote_addr if request else '0.0.0.0'
        except Exception:
            return '0.0.0.0'

    @staticmethod
    def log_login(user_id, username, success=True, failure_reason=None):
        """记录登录日志"""
        try:
            status = 'success' if success else 'failed'
            log = LoginLog(
                user_id=user_id,
                username=username,
                ip=LoginLogService.get_client_ip(),
                user_agent=(request.headers.get('User-Agent', '')[:255] if request else ''),
                status=status,
                timestamp=datetime.utcnow()
            )
            db.session.add(log)
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"记录登录日志失败: {e}")
            db.session.rollback()
            return False

    @staticmethod
    def log_logout(user_id, username):
        """记录登出日志"""
        try:
            log = LoginLog(
                user_id=user_id,
                username=username,
                ip=LoginLogService.get_client_ip(),
                user_agent=(request.headers.get('User-Agent', '')[:255] if request else ''),
                status='success',
                timestamp=datetime.utcnow()
            )
            db.session.add(log)
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"记录登出日志失败: {e}")
            db.session.rollback()
            return False

    @staticmethod
    def get_failed_attempts(username, minutes=5):
        """获取最近 N 分钟内该用户的登录失败次数"""
        try:
            from_time = datetime.utcnow() - timedelta(minutes=minutes)
            count = LoginLog.query.filter(
                LoginLog.username == username,
                LoginLog.status == 'failed',
                LoginLog.timestamp >= from_time
            ).count()
            return count
        except Exception as e:
            logger.error(f"查询失败登录次数失败: {e}")
            return 0

    @staticmethod
    def get_recent_logs(user_id=None, limit=50):
        """获取最近的登录日志"""
        try:
            q = LoginLog.query.order_by(LoginLog.timestamp.desc())
            if user_id is not None:
                q = q.filter(LoginLog.user_id == user_id)
            return q.limit(limit).all()
        except Exception as e:
            logger.error(f"查询登录日志失败: {e}")
            return []


def log_action(user_id=None, username=None, action=None, target=None, details=None, success=True, **_extra):
    """记录审计日志 - 接受任意额外 kwarg,记录到 LoginLog 表"""
    try:
        ip = LoginLogService.get_client_ip()
        ua = (request.headers.get('User-Agent', '')[:255] if request else '')
        status = 'success' if success else 'failed'
        # 把 action 和 details 合并存到 status 字段(因为 LoginLog 没有这些字段)
        # 用 action 作为日志描述前缀
        full_status = action or status
        if details and not success:
            full_status = f"{action}: {str(details)[:120]}" if action else str(details)[:120]
        log = LoginLog(
            user_id=user_id,
            username=username,
            ip=ip,
            user_agent=ua,
            status=full_status[:20],  # status 字段限长 20
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"记录审计日志失败: {e}")
        db.session.rollback()
        return False
