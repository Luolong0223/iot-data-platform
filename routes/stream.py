import json

from flask import Blueprint, Response, stream_with_context, current_app
from flask_login import login_required, current_user

stream_bp = Blueprint('stream', __name__, url_prefix='/api/stream')


@stream_bp.route('/events')
@login_required
def events():
    """SSE事件流端点 - 用于实时数据推送"""
    user_id = current_user.id
    
    def generate():
        try:
            yield 'data: ' + json.dumps({'type': 'connected'}) + '\n\n'
            
            # 导入realtime模块的推送函数
            from routes.realtime import get_realtime_stream
            
            # 获取实时数据流
            last_count = 0
            while True:
                # 获取最新数据
                stream_data = get_realtime_stream(user_id)
                current_count = len(stream_data)
                
                # 如果有新数据，发送
                if current_count > last_count:
                    new_data = stream_data[:current_count - last_count]  # 获取新增的数据
                    for data in new_data:
                        yield 'data: ' + json.dumps({
                            'type': 'data',
                            'data': data
                        }) + '\n\n'
                    last_count = current_count
                
                # 发送心跳
                yield 'data: ' + json.dumps({'type': 'heartbeat'}) + '\n\n'
                
        except GeneratorExit:
            pass
        except Exception as e:
            yield 'data: ' + json.dumps({'type': 'error', 'message': str(e)}) + '\n\n'

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@stream_bp.route('/device/<int:device_id>')
@login_required
def device_events(device_id):
    """单个设备的SSE事件流"""
    user_id = current_user.id
    
    def generate():
        try:
            yield 'data: ' + json.dumps({'type': 'connected', 'device_id': device_id}) + '\n\n'
            
            from routes.realtime import get_realtime_stream
            
            last_count = 0
            while True:
                stream_data = get_realtime_stream(user_id, device_id)
                current_count = len(stream_data)
                
                if current_count > last_count:
                    new_data = stream_data[:current_count - last_count]
                    for data in new_data:
                        yield 'data: ' + json.dumps({
                            'type': 'data',
                            'device_id': device_id,
                            'data': data
                        }) + '\n\n'
                    last_count = current_count
                
                yield 'data: ' + json.dumps({'type': 'heartbeat'}) + '\n\n'
                
        except GeneratorExit:
            pass
        except Exception as e:
            yield 'data: ' + json.dumps({'type': 'error', 'message': str(e)}) + '\n\n'

    return Response(stream_with_context(generate()), mimetype='text/event-stream')
