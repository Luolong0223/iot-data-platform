"""
数据备份路由
Data Backup Routes
"""
from flask import Blueprint, request, jsonify, session
from functools import wraps
from services.backup_service import BackupService, BackupScheduleService

backup_bp = Blueprint('backup', __name__, url_prefix='/api/backup')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function


@backup_bp.route('/backups', methods=['GET'])
@login_required
def list_backups():
    """获取备份列表"""
    user_id = session['user_id']
    backup_type = request.args.get('type')
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    result = BackupService.list_backups(
        user_id=user_id,
        backup_type=backup_type,
        status=status,
        page=page,
        per_page=per_page
    )
    
    return jsonify(result)


@backup_bp.route('/backups', methods=['POST'])
@login_required
def create_backup():
    """创建备份"""
    user_id = session['user_id']
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        backup = BackupService.create_backup(
            user_id=user_id,
            name=data['name'],
            backup_type=data.get('backup_type', 'full'),
            description=data.get('description'),
            parent_backup_id=data.get('parent_backup_id')
        )
        return jsonify(backup.to_dict()), 201
    except Exception as e:
        return jsonify({'error': f'创建备份失败: {str(e)}'}), 500


@backup_bp.route('/backups/<int:backup_id>', methods=['GET'])
@login_required
def get_backup(backup_id):
    """获取备份详情"""
    user_id = session['user_id']
    
    backup = BackupService.get_backup(backup_id, user_id)
    if not backup:
        return jsonify({'error': '备份不存在'}), 404
    
    return jsonify(backup.to_dict())


@backup_bp.route('/backups/<int:backup_id>', methods=['DELETE'])
@login_required
def delete_backup(backup_id):
    """删除备份"""
    user_id = session['user_id']
    
    try:
        BackupService.delete_backup(backup_id, user_id)
        return jsonify({'message': '备份已删除'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'删除备份失败: {str(e)}'}), 500


@backup_bp.route('/backups/<int:backup_id>/restore', methods=['POST'])
@login_required
def restore_backup(backup_id):
    """恢复备份"""
    user_id = session['user_id']
    
    try:
        result = BackupService.restore_backup(backup_id, user_id)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'恢复备份失败: {str(e)}'}), 500


@backup_bp.route('/statistics', methods=['GET'])
@login_required
def get_statistics():
    """获取备份统计"""
    user_id = session['user_id']
    
    try:
        result = BackupService.get_backup_statistics(user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'获取统计失败: {str(e)}'}), 500


@backup_bp.route('/cleanup', methods=['POST'])
@login_required
def cleanup_backups():
    """清理过期备份"""
    user_id = session['user_id']
    data = request.get_json() or {}
    retention_days = data.get('retention_days', 30)
    
    try:
        deleted_count = BackupService.cleanup_old_backups(user_id, retention_days)
        return jsonify({
            'message': f'已清理 {deleted_count} 个过期备份',
            'deleted_count': deleted_count
        })
    except Exception as e:
        return jsonify({'error': f'清理备份失败: {str(e)}'}), 500


# 备份定时任务路由

@backup_bp.route('/schedules', methods=['GET'])
@login_required
def list_schedules():
    """获取备份定时任务列表"""
    user_id = session['user_id']
    
    schedules = BackupScheduleService.list_schedules(user_id)
    return jsonify({
        'schedules': [s.to_dict() for s in schedules],
        'total': len(schedules)
    })


@backup_bp.route('/schedules', methods=['POST'])
@login_required
def create_schedule():
    """创建备份定时任务"""
    user_id = session['user_id']
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        schedule = BackupScheduleService.create_schedule(
            user_id=user_id,
            name=data['name'],
            backup_type=data.get('backup_type', 'full'),
            schedule_hour=data.get('schedule_hour', 2),
            schedule_day_of_week=data.get('schedule_day_of_week'),
            schedule_day_of_month=data.get('schedule_day_of_month'),
            retention_days=data.get('retention_days', 30),
            max_backups=data.get('max_backups', 10)
        )
        return jsonify(schedule.to_dict()), 201
    except Exception as e:
        return jsonify({'error': f'创建定时任务失败: {str(e)}'}), 500


@backup_bp.route('/schedules/<int:schedule_id>', methods=['PUT'])
@login_required
def update_schedule(schedule_id):
    """更新备份定时任务"""
    user_id = session['user_id']
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        schedule = BackupScheduleService.update_schedule(
            schedule_id=schedule_id,
            user_id=user_id,
            **data
        )
        return jsonify(schedule.to_dict())
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'更新定时任务失败: {str(e)}'}), 500


@backup_bp.route('/schedules/<int:schedule_id>', methods=['DELETE'])
@login_required
def delete_schedule(schedule_id):
    """删除备份定时任务"""
    user_id = session['user_id']
    
    try:
        BackupScheduleService.delete_schedule(schedule_id, user_id)
        return jsonify({'message': '定时任务已删除'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'删除定时任务失败: {str(e)}'}), 500


@backup_bp.route('/schedules/<int:schedule_id>/toggle', methods=['POST'])
@login_required
def toggle_schedule(schedule_id):
    """启用/禁用备份定时任务"""
    user_id = session['user_id']
    data = request.get_json()
    
    if not data or 'enabled' not in data:
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        schedule = BackupScheduleService.toggle_schedule(
            schedule_id=schedule_id,
            user_id=user_id,
            enabled=data['enabled']
        )
        return jsonify(schedule.to_dict())
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'操作失败: {str(e)}'}), 500
