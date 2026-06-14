"""设备模拟器路由 - 虚拟设备数据生成与测试"""
import logging
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from services.device_simulator import simulator

logger = logging.getLogger(__name__)

simulator_bp = Blueprint('simulator', __name__, url_prefix='/api/simulator')


@simulator_bp.route('', methods=['POST'])
@login_required
def create_simulator():
    """创建设备模拟器"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    device_id = data.get('device_id')
    if not device_id:
        return jsonify({'success': False, 'message': '请指定设备ID'}), 400
    
    config = {
        'metrics': data.get('metrics', ['temperature', 'humidity', 'voltage']),
        'interval': data.get('interval', 5),
        'data_range': data.get('data_range', {
            'temperature': {'min': 20, 'max': 40},
            'humidity': {'min': 40, 'max': 80},
            'voltage': {'min': 3000, 'max': 3600}
        }),
        'noise': data.get('noise', 0.1)
    }
    
    sim_config = simulator.create_simulator(current_user.id, device_id, config)
    
    return jsonify({
        'success': True,
        'message': '模拟器已创建',
        'simulator': sim_config
    }), 201


@simulator_bp.route('', methods=['GET'])
@login_required
def list_simulators():
    """列出所有模拟器"""
    simulators = simulator.list_simulators(user_id=current_user.id)
    return jsonify({
        'success': True,
        'simulators': simulators,
        'count': len(simulators)
    })


@simulator_bp.route('/<int:simulator_id>', methods=['GET'])
@login_required
def get_simulator(simulator_id):
    """获取模拟器详情"""
    sim_config = simulator.get_simulator(simulator_id)
    if not sim_config:
        return jsonify({'success': False, 'message': '模拟器不存在'}), 404
    
    if sim_config['user_id'] != current_user.id:
        return jsonify({'success': False, 'message': '无权访问'}), 403
    
    return jsonify({'success': True, 'simulator': sim_config})


@simulator_bp.route('/<int:simulator_id>/start', methods=['POST'])
@login_required
def start_simulator(simulator_id):
    """启动模拟器"""
    sim_config = simulator.get_simulator(simulator_id)
    if not sim_config:
        return jsonify({'success': False, 'message': '模拟器不存在'}), 404
    
    if sim_config['user_id'] != current_user.id:
        return jsonify({'success': False, 'message': '无权访问'}), 403
    
    success = simulator.start_simulator(simulator_id)
    
    return jsonify({
        'success': success,
        'message': '模拟器已启动' if success else '启动失败'
    })


@simulator_bp.route('/<int:simulator_id>/stop', methods=['POST'])
@login_required
def stop_simulator(simulator_id):
    """停止模拟器"""
    sim_config = simulator.get_simulator(simulator_id)
    if not sim_config:
        return jsonify({'success': False, 'message': '模拟器不存在'}), 404
    
    if sim_config['user_id'] != current_user.id:
        return jsonify({'success': False, 'message': '无权访问'}), 403
    
    success = simulator.stop_simulator(simulator_id)
    
    return jsonify({
        'success': success,
        'message': '模拟器已停止' if success else '停止失败'
    })


@simulator_bp.route('/<int:simulator_id>', methods=['DELETE'])
@login_required
def delete_simulator(simulator_id):
    """删除模拟器"""
    sim_config = simulator.get_simulator(simulator_id)
    if not sim_config:
        return jsonify({'success': False, 'message': '模拟器不存在'}), 404
    
    if sim_config['user_id'] != current_user.id:
        return jsonify({'success': False, 'message': '无权访问'}), 403
    
    success = simulator.delete_simulator(simulator_id)
    
    return jsonify({
        'success': success,
        'message': '模拟器已删除' if success else '删除失败'
    })


@simulator_bp.route('/generate', methods=['POST'])
@login_required
def generate_single_data():
    """手动生成单条数据"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    device_id = data.get('device_id')
    metric = data.get('metric', 'temperature')
    value = data.get('value')
    
    if not device_id:
        return jsonify({'success': False, 'message': '请指定设备ID'}), 400
    
    result = simulator.generate_single_data(device_id, metric, value)
    
    # 实际写入数据库
    from models.database import db, DataPoint, SlaveChannel
    from datetime import datetime
    
    try:
        # 查找或创建通道
        channel = SlaveChannel.query.filter_by(
            device_id=device_id,
            name=metric
        ).first()
        
        if not channel:
            channel = SlaveChannel(
                device_id=device_id,
                name=metric
            )
            db.session.add(channel)
            db.session.commit()
        
        # 创建数据点
        data_point = DataPoint(
            channel_id=channel.id,
            name=metric,
            value=result['value'],
            timestamp=datetime.utcnow()
        )
        db.session.add(data_point)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '数据已生成',
            'data': result
        })
    except Exception as e:
        logger.error(f"Failed to generate data: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@simulator_bp.route('/batch-generate', methods=['POST'])
@login_required
def batch_generate_data():
    """批量生成数据"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    device_id = data.get('device_id')
    metrics = data.get('metrics', ['temperature', 'humidity', 'voltage'])
    count = data.get('count', 10)
    
    if not device_id:
        return jsonify({'success': False, 'message': '请指定设备ID'}), 400
    
    from models.database import db, DataPoint, SlaveChannel
    from datetime import datetime, timedelta
    
    try:
        generated = []
        
        for metric in metrics:
            # 查找或创建通道
            channel = SlaveChannel.query.filter_by(
                device_id=device_id,
                name=metric
            ).first()
            
            if not channel:
                channel = SlaveChannel(
                    device_id=device_id,
                    name=metric
                )
                db.session.add(channel)
                db.session.commit()
            
            # 生成多条数据
            for i in range(count):
                result = simulator.generate_single_data(device_id, metric)
                
                data_point = DataPoint(
                    channel_id=channel.id,
                    name=metric,
                    value=result['value'],
                    timestamp=datetime.utcnow() - timedelta(minutes=i)
                )
                db.session.add(data_point)
                generated.append(result)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'已生成 {len(generated)} 条数据',
            'count': len(generated)
        })
    except Exception as e:
        logger.error(f"Failed to batch generate data: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
