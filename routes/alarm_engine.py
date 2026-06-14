"""
告警引擎 v2 API
提供去重/抑制/静默/升级/分组 高级能力
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from services.alarm_engine import get_engine
from services.rbac import require_permission

alarm_engine_bp = Blueprint('alarm_engine', __name__, url_prefix='/api/alarm-engine')


@alarm_engine_bp.route('/silences', methods=['GET'])
@login_required
@require_permission('alarm.read')
def list_silences():
    return jsonify({'success': True, 'data': get_engine().list_silences()})


@alarm_engine_bp.route('/silences', methods=['POST'])
@login_required
@require_permission('alarm.write')
def add_silence():
    data = request.get_json() or {}
    minutes = int(data.get('minutes', 30))
    matchers = data.get('matchers', {})
    if not matchers:
        return jsonify({'success': False, 'msg': 'matchers 必填，如 {"device":"d1","severity":"warning"}'}), 400
    rules = get_engine().add_silence(matchers, minutes, creator=current_user.username)
    return jsonify({'success': True, 'data': rules})


@alarm_engine_bp.route('/silences', methods=['DELETE'])
@login_required
@require_permission('alarm.write')
def clear_silences():
    get_engine().clear_silences()
    return jsonify({'success': True})


@alarm_engine_bp.route('/escalate', methods=['POST'])
@login_required
@require_permission('alarm.write')
def escalate():
    data = request.get_json() or {}
    minutes = int(data.get('minutes', 30))
    n = get_engine().escalate_overdue(minutes)
    return jsonify({'success': True, 'escalated': n})


@alarm_engine_bp.route('/statistics', methods=['GET'])
@login_required
@require_permission('alarm.read')
def statistics():
    user_id = None if current_user.is_admin else current_user.id
    return jsonify({'success': True, 'data': get_engine().statistics(user_id=user_id)})


@alarm_engine_bp.route('/grouped', methods=['GET'])
@login_required
@require_permission('alarm.read')
def grouped():
    user_id = None if current_user.is_admin else current_user.id
    limit = int(request.args.get('limit', 50))
    return jsonify({'success': True, 'data': get_engine().grouped_unhandled(user_id=user_id, limit=limit)})


@alarm_engine_bp.route('/test-trigger', methods=['POST'])
@login_required
@require_permission('alarm.write')
def test_trigger():
    """测试入口：手动触发一条告警（用于演示去重/抑制/静默效果）"""
    from services.alarm_engine import get_engine
    data = request.get_json() or {}
    eng = get_engine()
    # 先测静默
    candidate = {
        'user_id': current_user.id, 'rule_id': None,
        'device_name': data.get('device', 'test-device'),
        'point_name': data.get('point', 'temp'),
        'severity': data.get('severity', 'warning')
    }
    if eng.silences.is_silenced(candidate):
        return jsonify({'success': False, 'msg': '命中静默规则', 'silenced': True})
    alarm = eng.create_alarm(
        user_id=current_user.id,
        rule_id=None,
        device_name=data.get('device', 'test-device'),
        channel_name=data.get('channel', 'ch-1'),
        point_name=data.get('point', 'temp'),
        value=float(data.get('value', 99.9)),
        threshold=float(data.get('threshold', 80)),
        condition=data.get('condition', '>'),
        severity=data.get('severity', 'warning'),
        message=data.get('message', '')
    )
    if alarm is None:
        return jsonify({'success': False, 'msg': '告警被去重或抑制', 'deduped': True})
    return jsonify({'success': True, 'data': alarm.to_dict()})
