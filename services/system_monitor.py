"""
系统监控服务 - 服务健康/资源用量/慢查询监控
"""
import os
import psutil
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque

logger = logging.getLogger(__name__)


class SystemMonitorService:
    """系统监控服务"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.request_count = 0
        self.error_count = 0
        self.slow_queries = deque(maxlen=100)  # 保留最近100条慢查询
        self.request_history = deque(maxlen=1000)  # 保留最近1000条请求记录
    
    def get_system_info(self) -> Dict:
        """获取系统基本信息"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu': {
                    'percent': cpu_percent,
                    'count': psutil.cpu_count(),
                    'count_logical': psutil.cpu_count(logical=True)
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'used': memory.used,
                    'percent': memory.percent
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': disk.percent
                },
                'uptime': (datetime.now() - self.start_time).total_seconds()
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {}
    
    def get_service_health(self) -> Dict:
        """获取服务健康状态"""
        try:
            from flask import current_app
            from models.database import db, Device, DataPoint, AlarmRecord
            
            # 数据库连接测试
            db_healthy = True
            try:
                db.session.execute(db.text('SELECT 1'))
            except:
                db_healthy = False
            
            # 统计数据
            device_count = Device.query.count()
            data_point_count = DataPoint.query.count()
            alarm_count = AlarmRecord.query.filter_by(is_read=False).count()
            
            return {
                'status': 'healthy' if db_healthy else 'unhealthy',
                'database': {
                    'connected': db_healthy,
                    'type': current_app.config.get('SQLALCHEMY_DATABASE_URI', '').split(':')[0]
                },
                'statistics': {
                    'devices': device_count,
                    'data_points': data_point_count,
                    'unread_alarms': alarm_count
                },
                'uptime': (datetime.now() - self.start_time).total_seconds(),
                'request_count': self.request_count,
                'error_count': self.error_count
            }
        except Exception as e:
            logger.error(f"Failed to get service health: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_process_info(self) -> Dict:
        """获取当前进程信息"""
        try:
            process = psutil.Process()
            
            return {
                'pid': process.pid,
                'cpu_percent': process.cpu_percent(interval=0.1),
                'memory': {
                    'rss': process.memory_info().rss,
                    'vms': process.memory_info().vms,
                    'percent': process.memory_percent()
                },
                'threads': process.num_threads(),
                'connections': len(process.connections()),
                'create_time': datetime.fromtimestamp(process.create_time()).isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get process info: {e}")
            return {}
    
    def record_request(self, duration: float, status_code: int, endpoint: str):
        """记录请求信息"""
        self.request_count += 1
        if status_code >= 400:
            self.error_count += 1
        
        self.request_history.append({
            'timestamp': datetime.now().isoformat(),
            'duration': duration,
            'status_code': status_code,
            'endpoint': endpoint
        })
        
        # 记录慢查询（超过1秒）
        if duration > 1.0:
            self.slow_queries.append({
                'timestamp': datetime.now().isoformat(),
                'duration': duration,
                'endpoint': endpoint,
                'status_code': status_code
            })
    
    def get_slow_queries(self, limit: int = 20) -> List[Dict]:
        """获取慢查询记录"""
        return list(self.slow_queries)[-limit:]
    
    def get_request_stats(self, minutes: int = 60) -> Dict:
        """获取请求统计"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        
        recent_requests = [
            r for r in self.request_history
            if datetime.fromisoformat(r['timestamp']) > cutoff
        ]
        
        if not recent_requests:
            return {
                'total': 0,
                'avg_duration': 0,
                'max_duration': 0,
                'error_rate': 0
            }
        
        durations = [r['duration'] for r in recent_requests]
        errors = sum(1 for r in recent_requests if r['status_code'] >= 400)
        
        return {
            'total': len(recent_requests),
            'avg_duration': sum(durations) / len(durations),
            'max_duration': max(durations),
            'error_rate': errors / len(recent_requests) * 100
        }
    
    def get_all_metrics(self) -> Dict:
        """获取所有监控指标"""
        return {
            'system': self.get_system_info(),
            'service': self.get_service_health(),
            'process': self.get_process_info(),
            'requests': self.get_request_stats(),
            'slow_queries': self.get_slow_queries(10),
            'timestamp': datetime.now().isoformat()
        }


# 全局实例
system_monitor = SystemMonitorService()
