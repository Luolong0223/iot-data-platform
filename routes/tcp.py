from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from models.database import db, User
from config import config

tcp_bp = Blueprint('tcp', __name__, url_prefix='/api/tcp')


@tcp_bp.route('/config', methods=['GET'])
@login_required
def get_config():
    if current_user.is_admin:
        return jsonify({
            'success': True,
            'config': {
                'tcp_port': current_user.tcp_port,
                'storage_enabled': current_user.storage_enabled,
                'tcp_host': config['default'].TCP_HOST,
                'tcp_base_port': config['default'].TCP_BASE_PORT,
                'tcp_buffer_size': config['default'].TCP_BUFFER_SIZE,
                'tcp_timeout': config['default'].TCP_TIMEOUT,
                'session_lifetime': 24,
                'max_upload_size': 16
            }
        })
    return jsonify({
        'success': True,
        'config': {
            'tcp_port': current_user.tcp_port,
            'storage_enabled': current_user.storage_enabled
        }
    })


@tcp_bp.route('/config', methods=['PUT'])
@login_required
def update_config():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    if 'storage_enabled' in data:
        current_user.storage_enabled = bool(data['storage_enabled'])
        db.session.commit()

    return jsonify({
        'success': True,
        'config': {
            'tcp_port': current_user.tcp_port,
            'storage_enabled': current_user.storage_enabled
        }
    })
