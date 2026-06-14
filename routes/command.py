"""
命令中心路由
Command Center Routes
"""
import logging
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.command_service import CommandService, CommandTemplateService

logger = logging.getLogger(__name__)

command_bp = Blueprint('command', __name__, url_prefix='/api/command')


# ========================================================================
# 命令管理
# ========================================================================

@command_bp.route('/commands', methods=['POST'])
@login_required
def create_command():
    """创建设备命令"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        device_id = data.get('device_id')
        command = data.get('command')
        
        if not all([device_id, command]):
            return jsonify({'success': False, 'message': '缺少必填字段'}), 400
        
        cmd = CommandService.create_command(
            user_id=current_user.id,
            device_id=device_id,
            command=command,
            payload=data.get('payload'),
        )
        
        return jsonify({
            'success': True,
            'message': '命令创建成功',
            'command': cmd.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"创建命令失败: {e}")
        return jsonify({'success': False, 'message': '创建命令失败'}), 500


@command_bp.route('/commands/<int:command_id>/send', methods=['POST'])
@login_required
def send_command(command_id):
    """发送命令到设备"""
    try:
        cmd = CommandService.send_command(command_id, current_user.id)
        
        return jsonify({
            'success': True,
            'message': '命令已发送',
            'command': cmd.to_dict()
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"发送命令失败: {e}")
        return jsonify({'success': False, 'message': '发送命令失败'}), 500


@command_bp.route('/commands/<int:command_id>/status', methods=['PUT'])
@login_required
def update_command_status(command_id):
    """更新命令状态"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        status = data.get('status')
        if not status:
            return jsonify({'success': False, 'message': '缺少状态字段'}), 400
        
        cmd = CommandService.update_command_status(
            command_id=command_id,
            user_id=current_user.id,
            status=status,
            result=data.get('result'),
        )
        
        return jsonify({
            'success': True,
            'message': '命令状态已更新',
            'command': cmd.to_dict()
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"更新命令状态失败: {e}")
        return jsonify({'success': False, 'message': '更新命令状态失败'}), 500


@command_bp.route('/commands/<int:command_id>/cancel', methods=['POST'])
@login_required
def cancel_command(command_id):
    """取消命令"""
    try:
        cmd = CommandService.cancel_command(command_id, current_user.id)
        
        return jsonify({
            'success': True,
            'message': '命令已取消',
            'command': cmd.to_dict()
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"取消命令失败: {e}")
        return jsonify({'success': False, 'message': '取消命令失败'}), 500


@command_bp.route('/commands/<int:command_id>/retry', methods=['POST'])
@login_required
def retry_command(command_id):
    """重试命令"""
    try:
        cmd = CommandService.retry_command(command_id, current_user.id)
        
        return jsonify({
            'success': True,
            'message': '命令已重置，可以重新发送',
            'command': cmd.to_dict()
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"重试命令失败: {e}")
        return jsonify({'success': False, 'message': '重试命令失败'}), 500


@command_bp.route('/commands/<int:command_id>', methods=['GET'])
@login_required
def get_command(command_id):
    """获取命令详情"""
    try:
        cmd = CommandService.get_command(command_id, current_user.id)
        if not cmd:
            return jsonify({'success': False, 'message': '命令不存在'}), 404
        
        return jsonify({
            'success': True,
            'command': cmd.to_dict()
        })
        
    except Exception as e:
        logger.error(f"获取命令详情失败: {e}")
        return jsonify({'success': False, 'message': '获取命令详情失败'}), 500


@command_bp.route('/commands', methods=['GET'])
@login_required
def list_commands():
    """获取命令列表"""
    try:
        device_id = request.args.get('device_id', type=int)
        status = request.args.get('status')
        command = request.args.get('command')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        result = CommandService.list_commands(
            user_id=current_user.id,
            device_id=device_id,
            status=status,
            command=command,
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'success': True,
            'commands': result['commands'],
            'pagination': {
                'total': result['total'],
                'page': result['page'],
                'per_page': result['per_page'],
                'pages': result['pages']
            }
        })
        
    except Exception as e:
        logger.error(f"获取命令列表失败: {e}")
        return jsonify({'success': False, 'message': '获取命令列表失败'}), 500


@command_bp.route('/devices/<int:device_id>/pending-commands', methods=['GET'])
@login_required
def get_pending_commands(device_id):
    """获取设备的待发送命令"""
    try:
        commands = CommandService.get_pending_commands(device_id)
        
        return jsonify({
            'success': True,
            'commands': [cmd.to_dict() for cmd in commands],
            'count': len(commands)
        })
        
    except Exception as e:
        logger.error(f"获取待发送命令失败: {e}")
        return jsonify({'success': False, 'message': '获取待发送命令失败'}), 500


@command_bp.route('/statistics', methods=['GET'])
@login_required
def get_command_statistics():
    """获取命令统计"""
    try:
        days = request.args.get('days', 7, type=int)
        
        stats = CommandService.get_command_statistics(current_user.id, days)
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"获取命令统计失败: {e}")
        return jsonify({'success': False, 'message': '获取命令统计失败'}), 500


@command_bp.route('/cleanup', methods=['POST'])
@login_required
def cleanup_old_commands():
    """清理旧命令"""
    try:
        data = request.get_json() or {}
        days = data.get('days', 30)
        
        deleted = CommandService.cleanup_old_commands(current_user.id, days)
        
        return jsonify({
            'success': True,
            'message': f'已清理 {deleted} 条旧命令',
            'deleted_count': deleted
        })
        
    except Exception as e:
        logger.error(f"清理旧命令失败: {e}")
        return jsonify({'success': False, 'message': '清理旧命令失败'}), 500


# ========================================================================
# 命令模板管理
# ========================================================================

@command_bp.route('/templates', methods=['POST'])
@login_required
def create_template():
    """创建命令模板"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        name = data.get('name')
        command_type = data.get('command_type')
        
        if not all([name, command_type]):
            return jsonify({'success': False, 'message': '缺少必填字段'}), 400
        
        template = CommandTemplateService.create_template(
            user_id=current_user.id,
            name=name,
            command_type=command_type,
            description=data.get('description'),
            default_parameters=data.get('default_parameters'),
            default_timeout=data.get('default_timeout', 30),
            default_priority=data.get('default_priority', 5)
        )
        
        return jsonify({
            'success': True,
            'message': '模板创建成功',
            'template': template.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"创建模板失败: {e}")
        return jsonify({'success': False, 'message': '创建模板失败'}), 500


@command_bp.route('/templates/<int:template_id>', methods=['PUT'])
@login_required
def update_template(template_id):
    """更新命令模板"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        template = CommandTemplateService.update_template(
            template_id=template_id,
            user_id=current_user.id,
            **data
        )
        
        return jsonify({
            'success': True,
            'message': '模板更新成功',
            'template': template.to_dict()
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"更新模板失败: {e}")
        return jsonify({'success': False, 'message': '更新模板失败'}), 500


@command_bp.route('/templates/<int:template_id>', methods=['DELETE'])
@login_required
def delete_template(template_id):
    """删除命令模板"""
    try:
        CommandTemplateService.delete_template(template_id, current_user.id)
        
        return jsonify({
            'success': True,
            'message': '模板删除成功'
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"删除模板失败: {e}")
        return jsonify({'success': False, 'message': '删除模板失败'}), 500


@command_bp.route('/templates/<int:template_id>', methods=['GET'])
@login_required
def get_template(template_id):
    """获取模板详情"""
    try:
        template = CommandTemplateService.get_template(template_id, current_user.id)
        if not template:
            return jsonify({'success': False, 'message': '模板不存在'}), 404
        
        return jsonify({
            'success': True,
            'template': template.to_dict()
        })
        
    except Exception as e:
        logger.error(f"获取模板详情失败: {e}")
        return jsonify({'success': False, 'message': '获取模板详情失败'}), 500


@command_bp.route('/templates', methods=['GET'])
@login_required
def list_templates():
    """获取模板列表"""
    try:
        command_type = request.args.get('command_type')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        result = CommandTemplateService.list_templates(
            user_id=current_user.id,
            command_type=command_type,
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'success': True,
            'templates': result['templates'],
            'pagination': {
                'total': result['total'],
                'page': result['page'],
                'per_page': result['per_page'],
                'pages': result['pages']
            }
        })
        
    except Exception as e:
        logger.error(f"获取模板列表失败: {e}")
        return jsonify({'success': False, 'message': '获取模板列表失败'}), 500


@command_bp.route('/templates/<int:template_id>/execute', methods=['POST'])
@login_required
def execute_template(template_id):
    """从模板执行命令"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        device_id = data.get('device_id')
        if not device_id:
            return jsonify({'success': False, 'message': '缺少设备ID'}), 400
        
        cmd = CommandTemplateService.create_command_from_template(
            template_id=template_id,
            user_id=current_user.id,
            device_id=device_id,
            parameters=data.get('parameters')
        )
        
        return jsonify({
            'success': True,
            'message': '命令已从模板创建',
            'command': cmd.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"从模板执行命令失败: {e}")
        return jsonify({'success': False, 'message': '从模板执行命令失败'}), 500
