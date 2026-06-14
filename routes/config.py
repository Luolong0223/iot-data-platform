"""
配置中心路由
Configuration Center Routes
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.config_service import ConfigService

config_bp = Blueprint('config', __name__, url_prefix='/api/config')


@config_bp.route('/configs', methods=['GET'])
@login_required
def list_configs():
    """获取配置列表"""
    user_id = current_user.id
    group_name = request.args.get('group')
    enabled = request.args.get('enabled')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    enabled_bool = None
    if enabled is not None:
        enabled_bool = enabled.lower() == 'true'
    
    result = ConfigService.list_configs(
        user_id=user_id,
        group_name=group_name,
        enabled=enabled_bool,
        page=page,
        per_page=per_page
    )
    
    return jsonify(result)


@config_bp.route('/configs', methods=['POST'])
@login_required
def create_config():
    """创建配置"""
    user_id = current_user.id
    data = request.get_json()
    
    if not data or 'config_key' not in data:
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        config = ConfigService.create_config(
            user_id=user_id,
            config_key=data['config_key'],
            config_value=data.get('config_value'),
            value_type=data.get('value_type', 'string'),
            description=data.get('description'),
            group_name=data.get('group_name', 'default'),
            encrypted=data.get('encrypted', False)
        )
        return jsonify(config.to_dict()), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'创建配置失败: {str(e)}'}), 500


@config_bp.route('/configs/<int:config_id>', methods=['GET'])
@login_required
def get_config(config_id):
    """获取配置详情"""
    user_id = current_user.id
    
    config = ConfigService.get_config(config_id, user_id)
    if not config:
        return jsonify({'error': '配置不存在'}), 404
    
    return jsonify(config.to_dict())


@config_bp.route('/configs/<int:config_id>', methods=['PUT'])
@login_required
def update_config(config_id):
    """更新配置"""
    user_id = current_user.id
    data = request.get_json()
    
    if not data or 'config_value' not in data:
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        config = ConfigService.update_config(
            config_id=config_id,
            user_id=user_id,
            config_value=data['config_value'],
            change_note=data.get('change_note')
        )
        return jsonify(config.to_dict())
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'更新配置失败: {str(e)}'}), 500


@config_bp.route('/configs/<int:config_id>', methods=['DELETE'])
@login_required
def delete_config(config_id):
    """删除配置"""
    user_id = current_user.id
    
    try:
        ConfigService.delete_config(config_id, user_id)
        return jsonify({'message': '配置已删除'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'删除配置失败: {str(e)}'}), 500


@config_bp.route('/configs/<int:config_id>/toggle', methods=['POST'])
@login_required
def toggle_config(config_id):
    """启用/禁用配置"""
    user_id = current_user.id
    data = request.get_json()
    
    if not data or 'enabled' not in data:
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        config = ConfigService.toggle_config(
            config_id=config_id,
            user_id=user_id,
            enabled=data['enabled']
        )
        return jsonify(config.to_dict())
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'操作失败: {str(e)}'}), 500


@config_bp.route('/configs/<int:config_id>/rollback', methods=['POST'])
@login_required
def rollback_config(config_id):
    """回滚配置到指定版本"""
    user_id = current_user.id
    data = request.get_json()
    
    if not data or 'target_version' not in data:
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        config = ConfigService.rollback_config(
            config_id=config_id,
            user_id=user_id,
            target_version=data['target_version'],
            change_note=data.get('change_note')
        )
        return jsonify(config.to_dict())
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'回滚失败: {str(e)}'}), 500


@config_bp.route('/configs/<int:config_id>/versions', methods=['GET'])
@login_required
def list_versions(config_id):
    """获取配置版本历史"""
    user_id = current_user.id
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    try:
        result = ConfigService.list_versions(
            config_id=config_id,
            user_id=user_id,
            page=page,
            per_page=per_page
        )
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'获取版本历史失败: {str(e)}'}), 500


@config_bp.route('/configs/by-key/<config_key>', methods=['GET'])
@login_required
def get_config_by_key(config_key):
    """通过 key 获取配置"""
    user_id = current_user.id
    
    config = ConfigService.get_config_by_key(user_id, config_key)
    if not config:
        return jsonify({'error': '配置不存在'}), 404
    
    return jsonify(config.to_dict())


@config_bp.route('/configs/batch', methods=['GET'])
@login_required
def get_configs_batch():
    """批量获取配置"""
    user_id = current_user.id
    keys = request.args.get('keys', '').split(',')
    
    if not keys or keys == ['']:
        return jsonify({'error': '缺少 keys 参数'}), 400
    
    try:
        result = ConfigService.get_configs_batch(user_id, keys)
        return jsonify({'configs': result})
    except Exception as e:
        return jsonify({'error': f'获取配置失败: {str(e)}'}), 500


@config_bp.route('/configs/groups', methods=['GET'])
@login_required
def list_groups():
    """获取配置分组列表"""
    user_id = current_user.id
    
    try:
        result = ConfigService.list_groups(user_id)
        return jsonify({'groups': result})
    except Exception as e:
        return jsonify({'error': f'获取分组失败: {str(e)}'}), 500
