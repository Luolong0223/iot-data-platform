"""
多协议适配器路由
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models.database import db, ProtocolAdapter, ProtocolMessage
from services.protocol_adapter import ProtocolAdapterService
import logging

logger = logging.getLogger(__name__)

protocol_bp = Blueprint('protocol', __name__, url_prefix='/api/protocol')


@protocol_bp.route('/adapters', methods=['GET'])
@login_required
def list_adapters():
    """获取所有协议适配器"""
    adapters = ProtocolAdapter.query.filter_by(user_id=current_user.id).all()
    return jsonify({
        'success': True,
        'count': len(adapters),
        'adapters': [a.to_dict() for a in adapters]
    })


@protocol_bp.route('/adapters', methods=['POST'])
@login_required
def create_adapter():
    """创建协议适配器"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    name = data.get('name')
    protocol_type = data.get('protocol_type')
    connection_config = data.get('connection_config', {})
    parse_rules = data.get('parse_rules')
    
    if not name or not protocol_type:
        return jsonify({'success': False, 'message': '名称和协议类型不能为空'}), 400
    
    try:
        adapter = ProtocolAdapterService.create_adapter(
            user_id=current_user.id,
            name=name,
            protocol_type=protocol_type,
            connection_config=connection_config,
            parse_rules=parse_rules
        )
        return jsonify({
            'success': True,
            'message': '协议适配器创建成功',
            'adapter': adapter.to_dict()
        }), 201
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"创建协议适配器失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@protocol_bp.route('/adapters/<int:adapter_id>', methods=['GET'])
@login_required
def get_adapter(adapter_id):
    """获取协议适配器详情"""
    adapter = ProtocolAdapter.query.filter_by(id=adapter_id, user_id=current_user.id).first()
    if not adapter:
        return jsonify({'success': False, 'message': '适配器不存在'}), 404
    
    return jsonify({
        'success': True,
        'adapter': adapter.to_dict()
    })


@protocol_bp.route('/adapters/<int:adapter_id>', methods=['PUT'])
@login_required
def update_adapter(adapter_id):
    """更新协议适配器"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    try:
        adapter = ProtocolAdapterService.update_adapter(
            adapter_id=adapter_id,
            user_id=current_user.id,
            **data
        )
        return jsonify({
            'success': True,
            'message': '协议适配器更新成功',
            'adapter': adapter.to_dict()
        })
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"更新协议适配器失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@protocol_bp.route('/adapters/<int:adapter_id>', methods=['DELETE'])
@login_required
def delete_adapter(adapter_id):
    """删除协议适配器"""
    adapter = ProtocolAdapter.query.filter_by(id=adapter_id, user_id=current_user.id).first()
    if not adapter:
        return jsonify({'success': False, 'message': '适配器不存在'}), 404
    
    db.session.delete(adapter)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '协议适配器已删除'
    })


@protocol_bp.route('/adapters/<int:adapter_id>/test', methods=['POST'])
@login_required
def test_adapter_connection(adapter_id):
    """测试协议连接"""
    result = ProtocolAdapterService.test_connection(adapter_id, current_user.id)
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code


@protocol_bp.route('/adapters/<int:adapter_id>/enable', methods=['POST'])
@login_required
def enable_adapter(adapter_id):
    """启用协议适配器"""
    try:
        adapter = ProtocolAdapterService.update_adapter(
            adapter_id=adapter_id,
            user_id=current_user.id,
            is_enabled=True
        )
        return jsonify({
            'success': True,
            'message': '协议适配器已启用',
            'adapter': adapter.to_dict()
        })
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@protocol_bp.route('/adapters/<int:adapter_id>/disable', methods=['POST'])
@login_required
def disable_adapter(adapter_id):
    """禁用协议适配器"""
    try:
        adapter = ProtocolAdapterService.update_adapter(
            adapter_id=adapter_id,
            user_id=current_user.id,
            is_enabled=False
        )
        return jsonify({
            'success': True,
            'message': '协议适配器已禁用',
            'adapter': adapter.to_dict()
        })
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@protocol_bp.route('/adapters/<int:adapter_id>/messages', methods=['GET'])
@login_required
def get_adapter_messages(adapter_id):
    """获取适配器消息日志"""
    adapter = ProtocolAdapter.query.filter_by(id=adapter_id, user_id=current_user.id).first()
    if not adapter:
        return jsonify({'success': False, 'message': '适配器不存在'}), 404
    
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 20, type=int)
    direction = request.args.get('direction')  # inbound / outbound
    status = request.args.get('status')  # success / failed
    
    query = ProtocolMessage.query.filter_by(adapter_id=adapter_id)
    
    if direction:
        query = query.filter_by(direction=direction)
    if status:
        query = query.filter_by(status=status)
    
    query = query.order_by(ProtocolMessage.created_at.desc())
    pagination = query.paginate(page=page, per_page=size, error_out=False)
    
    return jsonify({
        'success': True,
        'messages': [m.to_dict() for m in pagination.items],
        'pagination': {
            'page': page,
            'size': size,
            'total': pagination.total,
            'pages': pagination.pages
        }
    })


@protocol_bp.route('/adapters/<int:adapter_id>/statistics', methods=['GET'])
@login_required
def get_adapter_statistics(adapter_id):
    """获取适配器统计信息"""
    stats = ProtocolAdapterService.get_adapter_statistics(adapter_id, current_user.id)
    if not stats:
        return jsonify({'success': False, 'message': '适配器不存在'}), 404
    
    return jsonify({
        'success': True,
        'statistics': stats
    })


@protocol_bp.route('/adapters/<int:adapter_id>/send', methods=['POST'])
@login_required
def send_message(adapter_id):
    """发送消息到设备"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    device_id = data.get('device_id')
    command = data.get('command', {})
    
    if not device_id:
        return jsonify({'success': False, 'message': '设备 ID 不能为空'}), 400
    
    result = ProtocolAdapterService.send_outbound_message(adapter_id, device_id, command)
    status_code = 200 if result.get('success') else 400
    
    return jsonify(result), status_code


@protocol_bp.route('/protocols', methods=['GET'])
@login_required
def list_supported_protocols():
    """获取支持的协议列表"""
    protocols = [
        {
            'type': 'mqtt',
            'name': 'MQTT',
            'description': '轻量级消息传输协议，适用于物联网设备',
            'config_fields': [
                {'name': 'broker', 'type': 'string', 'required': True, 'description': 'MQTT Broker 地址'},
                {'name': 'port', 'type': 'integer', 'required': True, 'default': 1883, 'description': '端口号'},
                {'name': 'username', 'type': 'string', 'required': False, 'description': '用户名'},
                {'name': 'password', 'type': 'string', 'required': False, 'description': '密码'},
                {'name': 'topic_prefix', 'type': 'string', 'required': False, 'default': 'iot/', 'description': '主题前缀'}
            ]
        },
        {
            'type': 'coap',
            'name': 'CoAP',
            'description': '受限应用协议，适用于低功耗设备',
            'config_fields': [
                {'name': 'host', 'type': 'string', 'required': True, 'description': 'CoAP 服务器地址'},
                {'name': 'port', 'type': 'integer', 'required': True, 'default': 5683, 'description': '端口号'}
            ]
        },
        {
            'type': 'modbus',
            'name': 'Modbus TCP',
            'description': '工业通信协议，适用于 PLC 和传感器',
            'config_fields': [
                {'name': 'host', 'type': 'string', 'required': True, 'description': 'Modbus 设备地址'},
                {'name': 'port', 'type': 'integer', 'required': True, 'default': 502, 'description': '端口号'},
                {'name': 'slave_id', 'type': 'integer', 'required': True, 'default': 1, 'description': '从站 ID'}
            ]
        },
        {
            'type': 'http',
            'name': 'HTTP/HTTPS',
            'description': '超文本传输协议，适用于 Web 设备',
            'config_fields': [
                {'name': 'url', 'type': 'string', 'required': True, 'description': '设备 API 地址'},
                {'name': 'method', 'type': 'string', 'required': False, 'default': 'POST', 'description': 'HTTP 方法'},
                {'name': 'headers', 'type': 'object', 'required': False, 'description': '请求头'}
            ]
        }
    ]
    
    return jsonify({
        'success': True,
        'protocols': protocols
    })
