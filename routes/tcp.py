from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from models.database import db, User

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
                'tcp_host': current_app.config.get('TCP_HOST', '0.0.0.0'),
                'tcp_base_port': current_app.config.get('TCP_BASE_PORT', 9105),
                'tcp_buffer_size': current_app.config.get('TCP_BUFFER_SIZE', 4096),
                'tcp_timeout': current_app.config.get('TCP_TIMEOUT', 30),
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
