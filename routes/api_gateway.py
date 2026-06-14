"""
API 网关路由
API Gateway Routes
"""
from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime
from services.api_gateway_service import APIKeyService, APIUsageService

api_gateway_bp = Blueprint('api_gateway', __name__, url_prefix='/api/gateway')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function


@api_gateway_bp.route('/keys', methods=['GET'])
@login_required
def list_api_keys():
    """获取 API Key 列表"""
    user_id = session['user_id']
    enabled = request.args.get('enabled')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    enabled_bool = None
    if enabled is not None:
        enabled_bool = enabled.lower() == 'true'
    
    result = APIKeyService.list_api_keys(
        user_id=user_id,
        enabled=enabled_bool,
        page=page,
        per_page=per_page
    )
    
    return jsonify(result)


@api_gateway_bp.route('/keys', methods=['POST'])
@login_required
def create_api_key():
    """创建 API Key"""
    user_id = session['user_id']
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        api_key = APIKeyService.create_api_key(
            user_id=user_id,
            name=data['name'],
            description=data.get('description'),
            permissions=data.get('permissions'),
            rate_limit_per_minute=data.get('rate_limit_per_minute', 60),
            rate_limit_per_hour=data.get('rate_limit_per_hour', 1000),
            rate_limit_per_day=data.get('rate_limit_per_day', 10000),
            expires_days=data.get('expires_days')
        )
        # 创建时返回完整 API Key
        return jsonify(api_key.to_dict_full()), 201
    except Exception as e:
        return jsonify({'error': f'创建 API Key 失败: {str(e)}'}), 500


@api_gateway_bp.route('/keys/<int:key_id>', methods=['GET'])
@login_required
def get_api_key(key_id):
    """获取 API Key 详情"""
    user_id = session['user_id']
    
    api_key = APIKeyService.get_api_key(key_id, user_id)
    if not api_key:
        return jsonify({'error': 'API Key 不存在'}), 404
    
    return jsonify(api_key.to_dict())


@api_gateway_bp.route('/keys/<int:key_id>', methods=['PUT'])
@login_required
def update_api_key(key_id):
    """更新 API Key"""
    user_id = session['user_id']
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        api_key = APIKeyService.update_api_key(
            api_key_id=key_id,
            user_id=user_id,
            name=data.get('name'),
            description=data.get('description'),
            permissions=data.get('permissions'),
            rate_limit_per_minute=data.get('rate_limit_per_minute'),
            rate_limit_per_hour=data.get('rate_limit_per_hour'),
            rate_limit_per_day=data.get('rate_limit_per_day'),
            expires_days=data.get('expires_days')
        )
        return jsonify(api_key.to_dict())
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'更新 API Key 失败: {str(e)}'}), 500


@api_gateway_bp.route('/keys/<int:key_id>', methods=['DELETE'])
@login_required
def delete_api_key(key_id):
    """删除 API Key"""
    user_id = session['user_id']
    
    try:
        APIKeyService.delete_api_key(key_id, user_id)
        return jsonify({'message': 'API Key 已删除'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'删除 API Key 失败: {str(e)}'}), 500


@api_gateway_bp.route('/keys/<int:key_id>/toggle', methods=['POST'])
@login_required
def toggle_api_key(key_id):
    """启用/禁用 API Key"""
    user_id = session['user_id']
    data = request.get_json()
    
    if not data or 'enabled' not in data:
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        api_key = APIKeyService.toggle_api_key(
            api_key_id=key_id,
            user_id=user_id,
            enabled=data['enabled']
        )
        return jsonify(api_key.to_dict())
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'操作失败: {str(e)}'}), 500


@api_gateway_bp.route('/keys/<int:key_id>/usage', methods=['GET'])
@login_required
def get_usage_logs(key_id):
    """获取 API Key 使用日志"""
    user_id = session['user_id']
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    
    start_dt = datetime.fromisoformat(start_time) if start_time else None
    end_dt = datetime.fromisoformat(end_time) if end_time else None
    
    try:
        result = APIUsageService.get_usage_logs(
            api_key_id=key_id,
            user_id=user_id,
            start_time=start_dt,
            end_time=end_dt,
            page=page,
            per_page=per_page
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'获取使用日志失败: {str(e)}'}), 500


@api_gateway_bp.route('/keys/<int:key_id>/statistics', methods=['GET'])
@login_required
def get_usage_statistics(key_id):
    """获取 API Key 使用统计"""
    user_id = session['user_id']
    days = request.args.get('days', 7, type=int)
    
    try:
        result = APIUsageService.get_usage_statistics(
            api_key_id=key_id,
            user_id=user_id,
            days=days
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'获取使用统计失败: {str(e)}'}), 500


@api_gateway_bp.route('/statistics', methods=['GET'])
@login_required
def get_all_statistics():
    """获取所有 API Key 的统计"""
    user_id = session['user_id']
    days = request.args.get('days', 7, type=int)
    
    try:
        result = APIUsageService.get_all_keys_statistics(
            user_id=user_id,
            days=days
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'获取统计失败: {str(e)}'}), 500


@api_gateway_bp.route('/validate', methods=['POST'])
def validate_api_key():
    """验证 API Key (公开接口)"""
    data = request.get_json()
    
    if not data or 'api_key' not in data:
        return jsonify({'error': '缺少 API Key'}), 400
    
    api_key = APIKeyService.validate_api_key(data['api_key'])
    
    if not api_key:
        return jsonify({'valid': False, 'error': 'API Key 无效或已过期'}), 401
    
    # 检查限流
    rate_check = APIKeyService.check_rate_limit(api_key)
    
    if not rate_check['allowed']:
        return jsonify({
            'valid': False,
            'error': '请求频率超限',
            'reason': rate_check['reason'],
            'limit': rate_check['limit'],
            'current': rate_check['current']
        }), 429
    
    return jsonify({
        'valid': True,
        'user_id': api_key.user_id,
        'permissions': api_key.permissions,
        'rate_limit': {
            'minute': rate_check['minute_usage'],
            'hour': rate_check['hour_usage'],
            'day': rate_check['day_usage']
        }
    })
