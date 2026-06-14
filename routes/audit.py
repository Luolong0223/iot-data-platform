"""审计日志路由 - 操作日志查询与统计"""
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, desc

from models.database import db, AuditLog
from services.rbac import require_permission

logger = logging.getLogger(__name__)

audit_bp = Blueprint('audit', __name__, url_prefix='/api/audit')


@audit_bp.route('/logs', methods=['GET'])
@login_required
@require_permission('audit.read')
def list_logs():
    """查询审计日志列表"""
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 20, type=int)
    
    # 过滤条件
    user_id = request.args.get('user_id', type=int)
    action = request.args.get('action')
    resource = request.args.get('resource')
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = AuditLog.query
    
    # 非管理员只能查看自己的日志
    if not current_user.is_admin:
        query = query.filter_by(user_id=current_user.id)
    elif user_id:
        query = query.filter_by(user_id=user_id)
    
    if action:
        query = query.filter_by(action=action)
    if resource:
        query = query.filter_by(resource=resource)
    if status:
        query = query.filter_by(status=status)
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(AuditLog.created_at >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(AuditLog.created_at < end_dt)
        except ValueError:
            pass
    
    # 分页
    total = query.count()
    logs = query.order_by(desc(AuditLog.created_at)).offset((page - 1) * size).limit(size).all()
    
    return jsonify({
        'success': True,
        'logs': [log.to_dict() for log in logs],
        'pagination': {
            'page': page,
            'size': size,
            'total': total,
            'pages': (total + size - 1) // size
        }
    })


@audit_bp.route('/logs/<int:log_id>', methods=['GET'])
@login_required
@require_permission('audit.read')
def get_log(log_id):
    """获取单条审计日志详情"""
    log = AuditLog.query.get(log_id)
    if not log:
        return jsonify({'success': False, 'message': '日志不存在'}), 404
    
    # 非管理员只能查看自己的日志
    if not current_user.is_admin and log.user_id != current_user.id:
        return jsonify({'success': False, 'message': '无权访问'}), 403
    
    return jsonify({'success': True, 'log': log.to_dict()})


@audit_bp.route('/statistics', methods=['GET'])
@login_required
@require_permission('audit.read')
def get_statistics():
    """获取审计日志统计信息"""
    days = request.args.get('days', 7, type=int)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # 基础查询
    base_query = AuditLog.query.filter(AuditLog.created_at >= start_date)
    
    # 非管理员只看自己
    if not current_user.is_admin:
        base_query = base_query.filter_by(user_id=current_user.id)
    
    # 总操作数
    total_actions = base_query.count()
    
    # 成功/失败统计
    success_count = base_query.filter_by(status='success').count()
    failed_count = base_query.filter_by(status='failed').count()
    
    # 按操作类型统计
    action_stats = db.session.query(
        AuditLog.action,
        func.count(AuditLog.id).label('count')
    ).filter(
        AuditLog.created_at >= start_date
    )
    if not current_user.is_admin:
        action_stats = action_stats.filter(AuditLog.user_id == current_user.id)
    action_stats = action_stats.group_by(AuditLog.action).all()
    
    # 按资源类型统计
    resource_stats = db.session.query(
        AuditLog.resource,
        func.count(AuditLog.id).label('count')
    ).filter(
        AuditLog.created_at >= start_date,
        AuditLog.resource.isnot(None)
    )
    if not current_user.is_admin:
        resource_stats = resource_stats.filter(AuditLog.user_id == current_user.id)
    resource_stats = resource_stats.group_by(AuditLog.resource).all()
    
    # 按日期统计（最近7天）
    daily_stats = []
    for i in range(days):
        day_start = start_date + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        
        day_query = AuditLog.query.filter(
            AuditLog.created_at >= day_start,
            AuditLog.created_at < day_end
        )
        if not current_user.is_admin:
            day_query = day_query.filter_by(user_id=current_user.id)
        
        count = day_query.count()
        daily_stats.append({
            'date': day_start.strftime('%Y-%m-%d'),
            'count': count
        })
    
    # 最活跃用户（仅管理员可见）
    top_users = []
    if current_user.is_admin:
        user_stats = db.session.query(
            AuditLog.username,
            func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.created_at >= start_date,
            AuditLog.username.isnot(None)
        ).group_by(AuditLog.username).order_by(desc('count')).limit(10).all()
        
        top_users = [{'username': u.username, 'count': u.count} for u in user_stats]
    
    return jsonify({
        'success': True,
        'statistics': {
            'period_days': days,
            'total_actions': total_actions,
            'success_count': success_count,
            'failed_count': failed_count,
            'success_rate': round(success_count / total_actions * 100, 2) if total_actions > 0 else 0,
            'action_breakdown': [{'action': a.action, 'count': a.count} for a in action_stats],
            'resource_breakdown': [{'resource': r.resource, 'count': r.count} for r in resource_stats],
            'daily_trend': daily_stats,
            'top_users': top_users
        }
    })


@audit_bp.route('/export', methods=['GET'])
@login_required
@require_permission('audit.export')
def export_logs():
    """导出审计日志"""
    import csv
    import io
    from flask import Response
    
    # 过滤条件
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = AuditLog.query
    
    # 非管理员只能导出自己的日志
    if not current_user.is_admin:
        query = query.filter_by(user_id=current_user.id)
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(AuditLog.created_at >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(AuditLog.created_at < end_dt)
        except ValueError:
            pass
    
    logs = query.order_by(desc(AuditLog.created_at)).limit(10000).all()
    
    # 生成 CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    writer.writerow(['ID', '用户', '操作', '资源', '资源ID', '详情', 'IP', '状态', '时间'])
    
    # 写入数据
    for log in logs:
        writer.writerow([
            log.id,
            log.username or '',
            log.action,
            log.resource or '',
            log.resource_id or '',
            log.detail or '',
            log.ip or '',
            log.status,
            log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else ''
        ])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=audit_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
    )


@audit_bp.route('/cleanup', methods=['POST'])
@login_required
@require_permission('audit.admin')
def cleanup_logs():
    """清理旧日志（仅管理员）"""
    days = request.json.get('days', 90)
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    deleted = AuditLog.query.filter(AuditLog.created_at < cutoff_date).delete()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'已清理 {deleted} 条 {days} 天前的日志'
    })
