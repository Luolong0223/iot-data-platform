"""
API 网关服务
API Gateway Service
"""
import json
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from models.database import db, APIKey, APIUsageLog, APIUsageStats
from sqlalchemy import desc, func

logger = logging.getLogger(__name__)


class APIKeyService:
    """API Key 管理服务"""
    
    @staticmethod
    def generate_api_key() -> str:
        """生成 API Key"""
        return f"iot_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def create_api_key(
        user_id: int,
        name: str,
        description: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        rate_limit_per_minute: int = 60,
        rate_limit_per_hour: int = 1000,
        rate_limit_per_day: int = 10000,
        expires_days: Optional[int] = None,
    ) -> APIKey:
        """创建 API Key"""
        api_key = APIKey(
            user_id=user_id,
            api_key=APIKeyService.generate_api_key(),
            name=name,
            description=description,
            permissions=json.dumps(permissions) if permissions else None,
            rate_limit_per_minute=rate_limit_per_minute,
            rate_limit_per_hour=rate_limit_per_hour,
            rate_limit_per_day=rate_limit_per_day,
            expires_at=datetime.utcnow() + timedelta(days=expires_days) if expires_days else None,
            enabled=True
        )
        
        db.session.add(api_key)
        db.session.commit()
        
        logger.info(f"创建 API Key: {api_key.id}, name: {name}")
        return api_key
    
    @staticmethod
    def update_api_key(
        api_key_id: int,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        rate_limit_per_minute: Optional[int] = None,
        rate_limit_per_hour: Optional[int] = None,
        rate_limit_per_day: Optional[int] = None,
        expires_days: Optional[int] = None,
    ) -> APIKey:
        """更新 API Key"""
        api_key = APIKey.query.filter_by(id=api_key_id, user_id=user_id).first()
        if not api_key:
            raise ValueError(f"API Key 不存在: {api_key_id}")
        
        if name is not None:
            api_key.name = name
        if description is not None:
            api_key.description = description
        if permissions is not None:
            api_key.permissions = json.dumps(permissions)
        if rate_limit_per_minute is not None:
            api_key.rate_limit_per_minute = rate_limit_per_minute
        if rate_limit_per_hour is not None:
            api_key.rate_limit_per_hour = rate_limit_per_hour
        if rate_limit_per_day is not None:
            api_key.rate_limit_per_day = rate_limit_per_day
        if expires_days is not None:
            api_key.expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        db.session.commit()
        
        logger.info(f"更新 API Key: {api_key.id}")
        return api_key
    
    @staticmethod
    def delete_api_key(api_key_id: int, user_id: int) -> bool:
        """删除 API Key"""
        api_key = APIKey.query.filter_by(id=api_key_id, user_id=user_id).first()
        if not api_key:
            raise ValueError(f"API Key 不存在: {api_key_id}")
        
        db.session.delete(api_key)
        db.session.commit()
        
        logger.info(f"删除 API Key: {api_key.id}")
        return True
    
    @staticmethod
    def toggle_api_key(api_key_id: int, user_id: int, enabled: bool) -> APIKey:
        """启用/禁用 API Key"""
        api_key = APIKey.query.filter_by(id=api_key_id, user_id=user_id).first()
        if not api_key:
            raise ValueError(f"API Key 不存在: {api_key_id}")
        
        api_key.enabled = enabled
        db.session.commit()
        
        logger.info(f"API Key 状态变更: {api_key.id}, enabled: {enabled}")
        return api_key
    
    @staticmethod
    def get_api_key(api_key_id: int, user_id: int) -> Optional[APIKey]:
        """获取 API Key 详情"""
        return APIKey.query.filter_by(id=api_key_id, user_id=user_id).first()
    
    @staticmethod
    def validate_api_key(api_key_str: str) -> Optional[APIKey]:
        """验证 API Key"""
        api_key = APIKey.query.filter_by(api_key=api_key_str).first()
        
        if not api_key:
            return None
        
        if not api_key.enabled:
            return None
        
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None
        
        # 更新最后使用时间
        api_key.last_used_at = datetime.utcnow()
        db.session.commit()
        
        return api_key
    
    @staticmethod
    def check_rate_limit(api_key: APIKey) -> Dict[str, Any]:
        """检查限流"""
        now = datetime.utcnow()
        
        # 检查每分钟限流
        minute_ago = now - timedelta(minutes=1)
        minute_count = APIUsageLog.query.filter(
            APIUsageLog.api_key_id == api_key.id,
            APIUsageLog.created_at >= minute_ago
        ).count()
        
        if minute_count >= api_key.rate_limit_per_minute:
            return {
                'allowed': False,
                'reason': 'rate_limit_minute',
                'limit': api_key.rate_limit_per_minute,
                'current': minute_count
            }
        
        # 检查每小时限流
        hour_ago = now - timedelta(hours=1)
        hour_count = APIUsageLog.query.filter(
            APIUsageLog.api_key_id == api_key.id,
            APIUsageLog.created_at >= hour_ago
        ).count()
        
        if hour_count >= api_key.rate_limit_per_hour:
            return {
                'allowed': False,
                'reason': 'rate_limit_hour',
                'limit': api_key.rate_limit_per_hour,
                'current': hour_count
            }
        
        # 检查每天限流
        day_ago = now - timedelta(days=1)
        day_count = APIUsageLog.query.filter(
            APIUsageLog.api_key_id == api_key.id,
            APIUsageLog.created_at >= day_ago
        ).count()
        
        if day_count >= api_key.rate_limit_per_day:
            return {
                'allowed': False,
                'reason': 'rate_limit_day',
                'limit': api_key.rate_limit_per_day,
                'current': day_count
            }
        
        return {
            'allowed': True,
            'minute_usage': minute_count,
            'hour_usage': hour_count,
            'day_usage': day_count
        }
    
    @staticmethod
    def list_api_keys(
        user_id: int,
        enabled: Optional[bool] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """获取 API Key 列表"""
        query = APIKey.query.filter_by(user_id=user_id)
        
        if enabled is not None:
            query = query.filter_by(enabled=enabled)
        
        query = query.order_by(desc(APIKey.created_at))
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'api_keys': [k.to_dict() for k in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }


class APIUsageService:
    """API 使用统计服务"""
    
    @staticmethod
    def log_usage(
        api_key_id: int,
        user_id: int,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> APIUsageLog:
        """记录 API 使用"""
        success = 200 <= status_code < 400
        
        log = APIUsageLog(
            api_key_id=api_key_id,
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message
        )
        
        db.session.add(log)
        
        # 更新 API Key 统计
        api_key = APIKey.query.get(api_key_id)
        if api_key:
            api_key.total_requests += 1
            if not success:
                api_key.total_errors += 1
        
        db.session.commit()
        
        return log
    
    @staticmethod
    def get_usage_logs(
        api_key_id: int,
        user_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        """获取使用日志"""
        query = APIUsageLog.query.filter_by(api_key_id=api_key_id, user_id=user_id)
        
        if start_time:
            query = query.filter(APIUsageLog.created_at >= start_time)
        if end_time:
            query = query.filter(APIUsageLog.created_at <= end_time)
        
        query = query.order_by(desc(APIUsageLog.created_at))
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'logs': [log.to_dict() for log in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    
    @staticmethod
    def get_usage_statistics(
        api_key_id: int,
        user_id: int,
        days: int = 7
    ) -> Dict[str, Any]:
        """获取使用统计"""
        start_time = datetime.utcnow() - timedelta(days=days)
        
        # 按天统计
        daily_stats = db.session.query(
            func.date(APIUsageLog.created_at).label('date'),
            func.count(APIUsageLog.id).label('total'),
            func.sum(func.cast(APIUsageLog.success, db.Integer)).label('successful'),
            func.avg(APIUsageLog.response_time_ms).label('avg_response_time')
        ).filter(
            APIUsageLog.api_key_id == api_key_id,
            APIUsageLog.user_id == user_id,
            APIUsageLog.created_at >= start_time
        ).group_by(
            func.date(APIUsageLog.created_at)
        ).all()
        
        # 按端点统计
        endpoint_stats = db.session.query(
            APIUsageLog.endpoint,
            func.count(APIUsageLog.id).label('count'),
            func.avg(APIUsageLog.response_time_ms).label('avg_response_time')
        ).filter(
            APIUsageLog.api_key_id == api_key_id,
            APIUsageLog.user_id == user_id,
            APIUsageLog.created_at >= start_time
        ).group_by(
            APIUsageLog.endpoint
        ).order_by(desc('count')).limit(10).all()
        
        # 总体统计
        total_stats = db.session.query(
            func.count(APIUsageLog.id).label('total'),
            func.sum(func.cast(APIUsageLog.success, db.Integer)).label('successful'),
            func.avg(APIUsageLog.response_time_ms).label('avg_response_time')
        ).filter(
            APIUsageLog.api_key_id == api_key_id,
            APIUsageLog.user_id == user_id,
            APIUsageLog.created_at >= start_time
        ).first()
        
        return {
            'period_days': days,
            'daily_stats': [
                {
                    'date': str(s.date),
                    'total': s.total,
                    'successful': s.successful or 0,
                    'failed': s.total - (s.successful or 0),
                    'avg_response_time_ms': round(s.avg_response_time or 0, 2)
                }
                for s in daily_stats
            ],
            'endpoint_stats': [
                {
                    'endpoint': s.endpoint,
                    'count': s.count,
                    'avg_response_time_ms': round(s.avg_response_time or 0, 2)
                }
                for s in endpoint_stats
            ],
            'summary': {
                'total_requests': total_stats.total or 0,
                'successful_requests': total_stats.successful or 0,
                'failed_requests': (total_stats.total or 0) - (total_stats.successful or 0),
                'success_rate': round((total_stats.successful or 0) / total_stats.total * 100, 2) if total_stats.total else 0,
                'avg_response_time_ms': round(total_stats.avg_response_time or 0, 2)
            }
        }
    
    @staticmethod
    def get_all_keys_statistics(
        user_id: int,
        days: int = 7
    ) -> Dict[str, Any]:
        """获取所有 API Key 的统计"""
        start_time = datetime.utcnow() - timedelta(days=days)
        
        api_keys = APIKey.query.filter_by(user_id=user_id).all()
        
        stats = []
        for key in api_keys:
            key_stats = db.session.query(
                func.count(APIUsageLog.id).label('total'),
                func.sum(func.cast(APIUsageLog.success, db.Integer)).label('successful')
            ).filter(
                APIUsageLog.api_key_id == key.id,
                APIUsageLog.created_at >= start_time
            ).first()
            
            stats.append({
                'api_key_id': key.id,
                'name': key.name,
                'enabled': key.enabled,
                'total_requests': key_stats.total or 0,
                'successful_requests': key_stats.successful or 0,
                'failed_requests': (key_stats.total or 0) - (key_stats.successful or 0)
            })
        
        return {
            'period_days': days,
            'keys_statistics': stats
        }
