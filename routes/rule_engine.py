"""
规则引擎 API 路由
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.rule_engine import RuleEngineService

rule_engine_bp = Blueprint('rule_engine', __name__, url_prefix='/api/rules')


@rule_engine_bp.route('', methods=['GET'])
@login_required
def get_rules():
    """获取所有规则"""
    enabled_only = request.args.get('enabled_only', 'false').lower() == 'true'
    rules = RuleEngineService.get_rules(current_user.id, enabled_only)
    return jsonify({
        'success': True,
        'data': rules,
        'count': len(rules)
    })


@rule_engine_bp.route('/<int:rule_id>', methods=['GET'])
@login_required
def get_rule(rule_id):
    """获取单个规则"""
    rule = RuleEngineService.get_rule(rule_id, current_user.id)
    if not rule:
        return jsonify({'success': False, 'error': '规则不存在'}), 404
    return jsonify({'success': True, 'data': rule})


@rule_engine_bp.route('', methods=['POST'])
@login_required
def create_rule():
    """创建规则"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '缺少请求数据'}), 400
    
    name = data.get('name')
    conditions = data.get('conditions')
    actions = data.get('actions', [])
    
    if not name or not conditions:
        return jsonify({'success': False, 'error': '缺少 name 或 conditions'}), 400
    
    result = RuleEngineService.create_rule(
        user_id=current_user.id,
        name=name,
        conditions=conditions,
        actions=actions,
        description=data.get('description'),
        is_enabled=data.get('is_enabled', True),
        priority=data.get('priority', 5),
        cooldown_seconds=data.get('cooldown_seconds', 300)
    )
    
    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 500


@rule_engine_bp.route('/<int:rule_id>', methods=['PUT'])
@login_required
def update_rule(rule_id):
    """更新规则"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '缺少请求数据'}), 400
    
    result = RuleEngineService.update_rule(rule_id, current_user.id, **data)
    
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400 if '不存在' in result.get('error', '') else 500


@rule_engine_bp.route('/<int:rule_id>', methods=['DELETE'])
@login_required
def delete_rule(rule_id):
    """删除规则"""
    result = RuleEngineService.delete_rule(rule_id, current_user.id)
    
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400 if '不存在' in result.get('error', '') else 500


@rule_engine_bp.route('/<int:rule_id>/enable', methods=['POST'])
@login_required
def enable_rule(rule_id):
    """启用规则"""
    result = RuleEngineService.update_rule(rule_id, current_user.id, is_enabled=True)
    if result['success']:
        return jsonify({'success': True, 'message': '规则已启用'})
    return jsonify(result), 400


@rule_engine_bp.route('/<int:rule_id>/disable', methods=['POST'])
@login_required
def disable_rule(rule_id):
    """禁用规则"""
    result = RuleEngineService.update_rule(rule_id, current_user.id, is_enabled=False)
    if result['success']:
        return jsonify({'success': True, 'message': '规则已禁用'})
    return jsonify(result), 400


@rule_engine_bp.route('/<int:rule_id>/test', methods=['POST'])
@login_required
def test_rule(rule_id):
    """测试规则"""
    data = request.get_json() or {}
    result = RuleEngineService.test_rule(rule_id, current_user.id, data)
    return jsonify(result)


@rule_engine_bp.route('/<int:rule_id>/logs', methods=['GET'])
@login_required
def get_execution_logs(rule_id):
    """获取规则执行日志"""
    limit = request.args.get('limit', 50, type=int)
    logs = RuleEngineService.get_execution_logs(rule_id, current_user.id, limit)
    return jsonify({
        'success': True,
        'data': logs,
        'count': len(logs)
    })


@rule_engine_bp.route('/evaluate', methods=['POST'])
@login_required
def evaluate_rules():
    """手动评估规则（用于测试）"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '缺少请求数据'}), 400
    
    device_id = data.get('device_id')
    metric = data.get('metric')
    value = data.get('value')
    
    if not all([device_id, metric, value is not None]):
        return jsonify({'success': False, 'error': '缺少 device_id, metric 或 value'}), 400
    
    results = RuleEngineService.evaluate_and_trigger(device_id, metric, float(value))
    
    return jsonify({
        'success': True,
        'triggered_rules': len(results),
        'results': results
    })
