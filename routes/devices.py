from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from models.database import db, Device

devices_bp = Blueprint('devices', __name__, url_prefix='/api/devices')


@devices_bp.route('', methods=['GET'])
@login_required
def list_devices():
    devices = Device.query.filter_by(user_id=current_user.id).all()
    return jsonify({'success': True, 'devices': [d.to_dict() for d in devices]})


@devices_bp.route('', methods=['POST'])
@login_required
def create_device():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    name = data.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'Device name is required'}), 400

    existing = Device.query.filter_by(user_id=current_user.id, name=name).first()
    if existing:
        return jsonify({'success': False, 'message': 'Device name already exists'}), 409

    device = Device(
        user_id=current_user.id,
        name=name,
        voltage_mv=data.get('voltage_mv')
    )
    db.session.add(device)
    db.session.commit()

    return jsonify({'success': True, 'device': device.to_dict()}), 201


@devices_bp.route('/<int:device_id>', methods=['PUT'])
@login_required
def update_device(device_id):
    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'message': 'Device not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    if 'name' in data:
        new_name = data['name'].strip()
        if new_name and new_name != device.name:
            existing = Device.query.filter_by(user_id=current_user.id, name=new_name).first()
            if existing:
                return jsonify({'success': False, 'message': 'Device name already exists'}), 409
            device.name = new_name

    if 'voltage_mv' in data:
        device.voltage_mv = data['voltage_mv']

    db.session.commit()
    return jsonify({'success': True, 'device': device.to_dict()})


@devices_bp.route('/<int:device_id>', methods=['DELETE'])
@login_required
def delete_device(device_id):
    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'message': 'Device not found'}), 404

    db.session.delete(device)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Device deleted'})


@devices_bp.route('/<int:device_id>/location', methods=['POST'])
@login_required
def set_location(device_id):
    device = Device.query.filter_by(id=device_id, user_id=current_user.id).first()
    if not device:
        return jsonify({'success': False, 'message': 'Device not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    latitude = data.get('latitude')
    longitude = data.get('longitude')
    location_name = data.get('location_name', '').strip()

    if latitude is not None:
        try:
            device.latitude = float(latitude)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid latitude'}), 400

    if longitude is not None:
        try:
            device.longitude = float(longitude)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid longitude'}), 400

    if location_name:
        device.location_name = location_name

    db.session.commit()
    return jsonify({'success': True, 'device': device.to_dict()})
