"""
健康检查路由 - 提供系统状态监控接口
"""
import os
import psutil
import platform
from datetime import datetime
from flask import Blueprint, jsonify
from flask_login import current_user

from models.database import db, User, Device, DataPoint, AlarmRecord, TcpLog
from services.tcp_handler import get_tcp_status

health_bp = Blueprint('health', __name__, url_prefix='/api/health')


@health_bp.route('', methods=['GET'])
def health_check():
    """
    基础健康检查接口
    用于负载均衡器和监控系统检测服务状态
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'iot-data-platform'
    })


@health_bp.route('/detailed', methods=['GET'])
def detailed_health():
    """
    详细健康检查接口
    包含数据库连接、TCP服务器状态等
    """
    checks = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {}
    }
    
    # 检查数据库连接
    try:
        db.session.execute(db.text('SELECT 1'))
        checks['checks']['database'] = {'status': 'ok', 'message': 'Database connection successful'}
    except Exception as e:
        checks['checks']['database'] = {'status': 'error', 'message': str(e)}
        checks['status'] = 'unhealthy'
    
    # 检查TCP服务器状态
    tcp_status = get_tcp_status()
    checks['checks']['tcp_server'] = {
        'status': 'ok' if tcp_status['running'] else 'warning',
        'message': f"TCP server {'running' if tcp_status['running'] else 'not running'}",
        'active_ports': tcp_status['active_ports']
    }
    
    return jsonify(checks)


@health_bp.route('/metrics', methods=['GET'])
def system_metrics():
    """
    系统指标接口
    返回系统资源和应用统计数据（应用统计走缓存 30s）
    """
    from services.cache import get_cache, make_key, cached
    cache = get_cache()
    app_stats = cache.get(make_key('app_stats'))
    if not app_stats:
        try:
            total_users = User.query.count()
            total_devices = Device.query.count()
            total_data_points = DataPoint.query.count()
            unread_alarms = AlarmRecord.query.filter_by(is_read=False).count()
            today_logs = TcpLog.query.filter(
                TcpLog.received_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
            ).count()
        except Exception:
            total_users = total_devices = total_data_points = unread_alarms = today_logs = 0
        app_stats = {
            'total_users': total_users,
            'total_devices': total_devices,
            'total_data_points': total_data_points,
            'unread_alarms': unread_alarms,
            'today_tcp_logs': today_logs,
        }
        try:
            cache.set(make_key('app_stats'), app_stats, ttl=30)
        except Exception:
            pass
    
    return jsonify({
        'timestamp': datetime.utcnow().isoformat(),
        'cache': cache.stats(),
        'system': {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_percent': psutil.cpu_percent(interval=None),
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'percent': psutil.virtual_memory().percent,
                'used': psutil.virtual_memory().used
            },
            'disk': {
                'total': psutil.disk_usage('/').total,
                'used': psutil.disk_usage('/').used,
                'free': psutil.disk_usage('/').free,
                'percent': psutil.disk_usage('/').percent
            }
        },
        'application': app_stats
    })


@health_bp.route('/ready', methods=['GET'])
def readiness():
    """
    就绪检查接口
    用于Kubernetes等容器编排系统的就绪探针
    """
    try:
        # 检查数据库是否可连接
        db.session.execute(db.text('SELECT 1'))
        return jsonify({'status': 'ready'}), 200
    except Exception as e:
        return jsonify({'status': 'not ready', 'error': str(e)}), 503


@health_bp.route('/live', methods=['GET'])
def liveness():
    """
    存活检查接口
    用于Kubernetes等容器编排系统的存活探针
    """
    return jsonify({'status': 'alive'}), 200
