"""
登录日志服务 - 记录用户登录行为
"""
import logging
from datetime import datetime
from flask import request
from models.database import db, LoginLog

logger = logging.getLogger(__name__)


class LoginLogService:
    """登录日志服务类"""
    
    @staticmethod
    def log_login(user_id, username, success=True, failure_reason=None):
        """
        记录登录尝试
        
        Args:
            user_id: 用户ID（登录失败时可能为None）
            username: 尝试登录的用户名
            success: 是否成功
            failure_reason: 失败原因
        """
        try:
            log = LoginLog(
                user_id=user_id,
                username=username,
                login_type='login',
                ip_address=LoginLogService.get_client_ip(),
                user_agent=request.headers.get('User-Agent', '')[:500],
                success=success,
                failure_reason=failure_reason
            )
            db.session.add(log)
            db.session.commit()
            
            if success:
                logger.info(f"User '{username}' logged in from {log.ip_address}")
            else:
                logger.warning(f"Failed login attempt for '{username}' from {log.ip_address}: {failure_reason}")
                
        except Exception as e:
            logger.error(f"Failed to log login attempt: {e}")
            db.session.rollback()
    
    @staticmethod
    def log_logout(user_id, username):
        """记录登出"""
        try:
            log = LoginLog(
                user_id=user_id,
                username=username,
                login_type='logout',
                ip_address=LoginLogService.get_client_ip(),
                user_agent=request.headers.get('User-Agent', '')[:500],
                success=True
            )
            db.session.add(log)
            db.session.commit()
            logger.info(f"User '{username}' logged out from {log.ip_address}")
        except Exception as e:
            logger.error(f"Failed to log logout: {e}")
            db.session.rollback()
    
    @staticmethod
    def get_client_ip():
        """获取客户端真实IP"""
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        return request.remote_addr or 'unknown'
    
    @staticmethod
    def get_recent_logs(user_id=None, limit=20):
        """
        获取最近的登录日志
        
        Args:
            user_id: 用户ID，None表示所有用户
            limit: 返回条数
        """
        query = LoginLog.query
        if user_id:
            query = query.filter_by(user_id=user_id)
        return query.order_by(LoginLog.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_failed_attempts(username, minutes=30):
        """
        获取指定时间内的失败登录次数
        
        Args:
            username: 用户名
            minutes: 时间范围（分钟）
        """
        from datetime import timedelta
        since = datetime.utcnow() - timedelta(minutes=minutes)
        return LoginLog.query.filter_by(
            username=username,
            success=False
        ).filter(
            LoginLog.created_at >= since
        ).count()
    
    @staticmethod
    def get_login_statistics(user_id=None, days=7):
        """
        获取登录统计
        
        Args:
            user_id: 用户ID，None表示所有用户
            days: 统计天数
        """
        from datetime import timedelta
        from sqlalchemy import func
        
        since = datetime.utcnow() - timedelta(days=days)
        query = db.session.query(
            func.date(LoginLog.created_at).label('date'),
            LoginLog.login_type,
            func.count().label('count')
        ).filter(
            LoginLog.created_at >= since
        )
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        query = query.group_by(
            func.date(LoginLog.created_at),
            LoginLog.login_type
        ).all()
        
        return [
            {
                'date': str(row.date),
                'type': row.login_type,
                'count': row.count
            }
            for row in query
        ]
