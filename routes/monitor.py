"""
系统监控路由
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from services.system_monitor import system_monitor
import logging

logger = logging.getLogger(__name__)

monitor_bp = Blueprint('monitor', __name__, url_prefix='/api/monitor')


@monitor_bp.route('/system', methods=['GET'])
@login_required
def get_system_info():
    """获取系统信息"""
    try:
        info = system_monitor.get_system_info()
        return jsonify({'success': True, 'data': info})
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@monitor_bp.route('/health', methods=['GET'])
@login_required
def get_service_health():
    """获取服务健康状态"""
    try:
        health = system_monitor.get_service_health()
        return jsonify({'success': True, 'data': health})
    except Exception as e:
        logger.error(f"Failed to get service health: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@monitor_bp.route('/process', methods=['GET'])
@login_required
def get_process_info():
    """获取进程信息"""
    try:
        info = system_monitor.get_process_info()
        return jsonify({'success': True, 'data': info})
    except Exception as e:
        logger.error(f"Failed to get process info: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@monitor_bp.route('/slow-queries', methods=['GET'])
@login_required
def get_slow_queries():
    """获取慢查询记录"""
    try:
        limit = request.args.get('limit', 20, type=int)
        queries = system_monitor.get_slow_queries(limit)
        return jsonify({'success': True, 'data': queries, 'count': len(queries)})
    except Exception as e:
        logger.error(f"Failed to get slow queries: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@monitor_bp.route('/requests', methods=['GET'])
@login_required
def get_request_stats():
    """获取请求统计"""
    try:
        minutes = request.args.get('minutes', 60, type=int)
        stats = system_monitor.get_request_stats(minutes)
        return jsonify({'success': True, 'data': stats})
    except Exception as e:
        logger.error(f"Failed to get request stats: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@monitor_bp.route('/all', methods=['GET'])
@login_required
def get_all_metrics():
    """获取所有监控指标"""
    try:
        metrics = system_monitor.get_all_metrics()
        return jsonify({'success': True, 'data': metrics})
    except Exception as e:
        logger.error(f"Failed to get all metrics: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
