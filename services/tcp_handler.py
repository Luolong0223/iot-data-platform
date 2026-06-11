import asyncio
import json
import logging
import os
import threading
from datetime import datetime

from models.database import db, User, Device, SlaveChannel, DataPoint, TcpLog, AlarmRule, AlarmRecord
from services.data_parser import parse_tcp_data

logger = logging.getLogger(__name__)

# 添加文件日志处理器
log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tcp_handler.log')
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# SSE 客户端管理
_sse_clients = []
_sse_lock = threading.Lock()


def register_sse_client():
    event = threading.Event()
    queue = []
    client = {'event': event, 'queue': queue}
    with _sse_lock:
        _sse_clients.append(client)
    return client


def unregister_sse_client(client):
    with _sse_lock:
        if client in _sse_clients:
            _sse_clients.remove(client)


def notify_sse_clients(data):
    with _sse_lock:
        for client in _sse_clients:
            client['queue'].append(data)
            client['event'].set()


class TcpConnectionHandler:
    def __init__(self, app, user_id):
        self.app = app
        self.user_id = user_id

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        logger.info(f"TCP connection from {addr} for user {self.user_id}")

        try:
            while True:
                data = await asyncio.wait_for(
                    reader.read(self.app.config.get('TCP_BUFFER_SIZE', 4096)),
                    timeout=self.app.config.get('TCP_TIMEOUT', 30)
                )
                if not data:
                    break

                raw_data = data.decode('utf-8', errors='replace').strip()
                if not raw_data:
                    continue

                await self.process_data(raw_data)

        except asyncio.TimeoutError:
            logger.info(f"TCP connection timeout for {addr}")
        except Exception as e:
            logger.error(f"TCP connection error for {addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            logger.info(f"TCP connection closed for {addr}")

    async def process_data(self, raw_data):
        with self.app.app_context():
            user = User.query.get(self.user_id)
            if not user:
                logger.error(f"User {self.user_id} not found")
                return

            parsed = False
            error_msg = None

            try:
                result = parse_tcp_data(raw_data)
                parsed = True

                if user.storage_enabled:
                    self.store_data(user.id, result)
                    # 推送 SSE 新数据事件
                    for ch in result['channels']:
                        for dp in ch['data_points']:
                            notify_sse_clients({
                                'type': 'new_data',
                                'device_name': result['device_name'],
                                'channel_name': ch['name'],
                                'point_name': dp['name'],
                                'value': dp['value'],
                                'timestamp': datetime.utcnow().isoformat()
                            })
                    self.check_alarms(user.id, result)

            except ValueError as e:
                error_msg = str(e)
                logger.warning(f"Failed to parse TCP data for user {self.user_id}: {error_msg}")

            tcp_log = TcpLog(
                user_id=user.id,
                raw_data=raw_data,
                parsed=parsed,
                error_msg=error_msg
            )
            db.session.add(tcp_log)
            db.session.commit()

    def store_data(self, user_id, result):
        device_name = result['device_name']
        voltage_mv = result['voltage_mv']

        device = Device.query.filter_by(user_id=user_id, name=device_name).first()
        if not device:
            device = Device(
                user_id=user_id,
                name=device_name,
                voltage_mv=voltage_mv
            )
            db.session.add(device)
            db.session.flush()
        else:
            if voltage_mv is not None:
                device.voltage_mv = voltage_mv

        for ch in result['channels']:
            channel = SlaveChannel.query.filter_by(device_id=device.id, name=ch['name']).first()
            if not channel:
                channel = SlaveChannel(
                    device_id=device.id,
                    name=ch['name'],
                    online=ch['online']
                )
                db.session.add(channel)
                db.session.flush()
            else:
                channel.online = ch['online']

            for dp in ch['data_points']:
                data_point = DataPoint(
                    channel_id=channel.id,
                    name=dp['name'],
                    value=dp['value']
                )
                db.session.add(data_point)

        db.session.commit()
        logger.info(f"Stored data for user {user_id}, device {device_name}")

    def check_alarms(self, user_id, result):
        rules = AlarmRule.query.filter_by(user_id=user_id, enabled=True).all()
        if not rules:
            return

        device_name = result['device_name']
        records_to_create = []
        notifications = []

        for ch in result['channels']:
            channel_name = ch['name']
            for dp in ch['data_points']:
                point_name = dp['name']
                value = dp['value']
                for rule in rules:
                    if (rule.device_name == device_name and
                            rule.channel_name == channel_name and
                            rule.point_name == point_name):
                        triggered = False
                        if rule.condition == 'gt' and value > rule.threshold:
                            triggered = True
                        elif rule.condition == 'lt' and value < rule.threshold:
                            triggered = True
                        elif rule.condition == 'eq' and value == rule.threshold:
                            triggered = True

                        if triggered:
                            message = (
                                f"Alarm: {device_name}/{channel_name}/{point_name} = {value} "
                                f"({rule.condition} {rule.threshold})"
                            )
                            record = AlarmRecord(
                                user_id=user_id,
                                rule_id=rule.id,
                                device_name=device_name,
                                channel_name=channel_name,
                                point_name=point_name,
                                value=value,
                                threshold=rule.threshold,
                                condition=rule.condition,
                                message=message
                            )
                            records_to_create.append(record)
                            notifications.append({
                                'type': 'alarm',
                                'device_name': device_name,
                                'channel_name': channel_name,
                                'point_name': point_name,
                                'value': value,
                                'threshold': rule.threshold,
                                'condition': rule.condition,
                                'message': message,
                                'timestamp': datetime.utcnow().isoformat()
                            })
                            logger.warning(message)

        if records_to_create:
            for record in records_to_create:
                db.session.add(record)
            db.session.commit()
            for notification in notifications:
                notify_sse_clients(notification)
