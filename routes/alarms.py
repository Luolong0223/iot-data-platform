from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from models.database import db, AlarmRule, AlarmRecord

alarms_bp = Blueprint('alarms', __name__, url_prefix='/api/alarms')


@alarms_bp.route('/rules', methods=['GET'])
@login_required
def list_rules():
    rules = AlarmRule.query.filter_by(user_id=current_user.id).all()
    return jsonify({'success': True, 'rules': [r.to_dict() for r in rules]})


@alarms_bp.route('/rules', methods=['POST'])
@login_required
def create_rule():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    device_name = data.get('device_name', '').strip()
    channel_name = data.get('channel_name', '').strip()
    point_name = data.get('point_name', '').strip()
    condition = data.get('condition', '').strip()
    threshold = data.get('threshold')
    enabled = data.get('enabled', True)

    if not all([device_name, channel_name, point_name, condition]):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    if condition not in ('gt', 'lt', 'eq'):
        return jsonify({'success': False, 'message': 'Invalid condition'}), 400

    try:
        threshold = float(threshold)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid threshold'}), 400

    rule = AlarmRule(
        user_id=current_user.id,
        device_name=device_name,
        channel_name=channel_name,
        point_name=point_name,
        condition=condition,
        threshold=threshold,
        enabled=bool(enabled)
    )
    db.session.add(rule)
    db.session.commit()

    return jsonify({'success': True, 'rule': rule.to_dict()}), 201


@alarms_bp.route('/rules/<int:rule_id>', methods=['PUT'])
@login_required
def update_rule(rule_id):
    rule = AlarmRule.query.filter_by(id=rule_id, user_id=current_user.id).first()
    if not rule:
        return jsonify({'success': False, 'message': 'Rule not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    if 'device_name' in data:
        rule.device_name = data['device_name'].strip()
    if 'channel_name' in data:
        rule.channel_name = data['channel_name'].strip()
    if 'point_name' in data:
        rule.point_name = data['point_name'].strip()
    if 'condition' in data:
        condition = data['condition'].strip()
        if condition not in ('gt', 'lt', 'eq'):
            return jsonify({'success': False, 'message': 'Invalid condition'}), 400
        rule.condition = condition
    if 'threshold' in data:
        try:
            rule.threshold = float(data['threshold'])
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid threshold'}), 400
    if 'enabled' in data:
        rule.enabled = bool(data['enabled'])

    db.session.commit()
    return jsonify({'success': True, 'rule': rule.to_dict()})


@alarms_bp.route('/rules/<int:rule_id>', methods=['DELETE'])
@login_required
def delete_rule(rule_id):
    rule = AlarmRule.query.filter_by(id=rule_id, user_id=current_user.id).first()
    if not rule:
        return jsonify({'success': False, 'message': 'Rule not found'}), 404

    db.session.delete(rule)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Rule deleted'})


@alarms_bp.route('/records', methods=['GET'])
@login_required
def list_records():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    if per_page > 100:
        per_page = 100

    query = AlarmRecord.query.filter_by(user_id=current_user.id).order_by(AlarmRecord.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'success': True,
        'records': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page,
        'per_page': per_page
    })


@alarms_bp.route('/records/<int:record_id>/read', methods=['PUT'])
@login_required
def mark_record_read(record_id):
    record = AlarmRecord.query.filter_by(id=record_id, user_id=current_user.id).first()
    if not record:
        return jsonify({'success': False, 'message': 'Record not found'}), 404

    record.is_read = True
    db.session.commit()
    return jsonify({'success': True, 'record': record.to_dict()})
