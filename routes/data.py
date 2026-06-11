import os
import csv
import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from models.database import db, Device, SlaveChannel, DataPoint

data_bp = Blueprint('data', __name__, url_prefix='/api/data')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'csv', 'json'}


@data_bp.route('/latest', methods=['GET'])
@login_required
def latest_data():
    devices = Device.query.filter_by(user_id=current_user.id).all()
    result = []
    for device in devices:
        device_data = device.to_dict()
        device_data['channels'] = []
        for channel in device.channels:
            ch_data = channel.to_dict()
            latest_points = DataPoint.query.filter_by(channel_id=channel.id).order_by(DataPoint.timestamp.desc()).limit(10).all()
            ch_data['latest_points'] = [dp.to_dict() for dp in latest_points]
            device_data['channels'].append(ch_data)
        result.append(device_data)

    return jsonify({'success': True, 'devices': result})


@data_bp.route('/history', methods=['GET'])
@login_required
def history_data():
    device_id = request.args.get('device_id', type=int)
    channel_id = request.args.get('channel_id', type=int)
    point_name = request.args.get('point_name', '').strip()
    limit = request.args.get('limit', 100, type=int)

    query = DataPoint.query.join(SlaveChannel).join(Device).filter(Device.user_id == current_user.id)

    if device_id:
        query = query.filter(Device.id == device_id)
    if channel_id:
        query = query.filter(SlaveChannel.id == channel_id)
    if point_name:
        query = query.filter(DataPoint.name == point_name)

    points = query.order_by(DataPoint.timestamp.desc()).limit(limit).all()
    return jsonify({'success': True, 'data': [p.to_dict() for p in points]})


@data_bp.route('/chart/<int:channel_id>/<point_name>', methods=['GET'])
@login_required
def chart_data(channel_id, point_name):
    channel = SlaveChannel.query.join(Device).filter(
        SlaveChannel.id == channel_id,
        Device.user_id == current_user.id
    ).first()

    if not channel:
        return jsonify({'success': False, 'message': 'Channel not found'}), 404

    hours = request.args.get('hours', 24, type=int)
    since = datetime.utcnow() - timedelta(hours=hours)

    points = DataPoint.query.filter(
        DataPoint.channel_id == channel_id,
        DataPoint.name == point_name,
        DataPoint.timestamp >= since
    ).order_by(DataPoint.timestamp.asc()).all()

    return jsonify({
        'success': True,
        'channel': channel.to_dict(),
        'point_name': point_name,
        'labels': [p.timestamp.isoformat() for p in points],
        'values': [p.value for p in points]
    })


@data_bp.route('/upload', methods=['POST'])
@login_required
def file_upload():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Only CSV and JSON files are allowed'}), 400

    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)

    filename = secure_filename(file.filename)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    try:
        ext = filename.rsplit('.', 1)[1].lower()
        if ext == 'csv':
            imported = import_csv(filepath, current_user.id)
        elif ext == 'json':
            imported = import_json(filepath, current_user.id)
        else:
            imported = 0

        return jsonify({'success': True, 'message': f'File uploaded, {imported} records imported'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Import failed: {str(e)}'}), 500


def import_csv(filepath, user_id):
    imported = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            device_name = row.get('device_name', '').strip()
            channel_name = row.get('channel_name', '').strip()
            point_name = row.get('point_name', '').strip()
            value_str = row.get('value', '').strip()
            timestamp_str = row.get('timestamp', '').strip()

            if not all([device_name, channel_name, point_name, value_str]):
                continue

            try:
                value = float(value_str)
            except ValueError:
                continue

            device = Device.query.filter_by(user_id=user_id, name=device_name).first()
            if not device:
                device = Device(user_id=user_id, name=device_name)
                db.session.add(device)
                db.session.flush()

            channel = SlaveChannel.query.filter_by(device_id=device.id, name=channel_name).first()
            if not channel:
                channel = SlaveChannel(device_id=device.id, name=channel_name, online=True)
                db.session.add(channel)
                db.session.flush()

            dp = DataPoint(channel_id=channel.id, name=point_name, value=value)
            if timestamp_str:
                try:
                    dp.timestamp = datetime.fromisoformat(timestamp_str)
                except ValueError:
                    pass

            db.session.add(dp)
            imported += 1

    db.session.commit()
    return imported


def import_json(filepath, user_id):
    imported = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, list):
        data = [data]

    for item in data:
        if not isinstance(item, dict):
            continue

        device_name = item.get('device_name', '').strip()
        channel_name = item.get('channel_name', '').strip()
        point_name = item.get('point_name', '').strip()
        value = item.get('value')
        timestamp_str = item.get('timestamp', '').strip()

        if not all([device_name, channel_name, point_name]) or value is None:
            continue

        try:
            value = float(value)
        except ValueError:
            continue

        device = Device.query.filter_by(user_id=user_id, name=device_name).first()
        if not device:
            device = Device(user_id=user_id, name=device_name)
            db.session.add(device)
            db.session.flush()

        channel = SlaveChannel.query.filter_by(device_id=device.id, name=channel_name).first()
        if not channel:
            channel = SlaveChannel(device_id=device.id, name=channel_name, online=True)
            db.session.add(channel)
            db.session.flush()

        dp = DataPoint(channel_id=channel.id, name=point_name, value=value)
        if timestamp_str:
            try:
                dp.timestamp = datetime.fromisoformat(timestamp_str)
            except ValueError:
                pass

        db.session.add(dp)
        imported += 1

    db.session.commit()
    return imported
