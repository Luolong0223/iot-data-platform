import json
import logging
import threading
from datetime import datetime
from decimal import Decimal, InvalidOperation

from models.database import db, User, Device, Channel, DataPoint, DataHistory, TcpLog
from services.tcp_parser import parse_message

logger = logging.getLogger(__name__)

_tcp_stats = {
    'total_connections': 0,
    'total_messages': 0,
    'last_activity': None
}
_tcp_stats_lock = threading.Lock()


def process_tcp_data(user_id, raw_data, client_ip=None):
    """处理单条 TCP 数据（供 tcp_server.py 调用）"""
    from flask import current_app
    with current_app.app_context():
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return

        parsed = False
        error_msg = None

        try:
            parsed_msg = parse_message(raw_data)
            parsed = True
            store_data(user_id, parsed_msg)
        except ValueError as e:
            error_msg = str(e)
            logger.warning(f"Failed to parse TCP data for user {user_id}: {error_msg}")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Database error for user {user_id}: {e}", exc_info=True)

        try:
            tcp_log = TcpLog(
                port=user_id,
                client_ip=client_ip,
                direction='in',
                content=raw_data[:2000] if raw_data else '',
                status='success' if parsed else 'error',
                error_message=error_msg
            )
            db.session.add(tcp_log)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to save TCP log: {e}")
            db.session.rollback()


def get_tcp_status():
    from tcp_server import servers
    with _tcp_stats_lock:
        stats = _tcp_stats.copy()
    return {
        'running': len(servers) > 0,
        'active_ports': list(servers.keys()),
        'total_connections': stats['total_connections'],
        'total_messages': stats['total_messages'],
        'last_activity': stats['last_activity'].isoformat() if stats['last_activity'] else None
    }


class TcpConnectionHandler:
    def __init__(self, app, user_id):
        self.app = app
        self.user_id = user_id

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        logger.info(f"TCP connection from {addr} for user {self.user_id}")

        try:
            while True:
                try:
                    data = await asyncio.wait_for(
                        reader.read(self.app.config.get('TCP_BUFFER_SIZE', 4096)),
                        timeout=self.app.config.get('TCP_TIMEOUT', 300)
                    )
                except asyncio.TimeoutError:
                    logger.info(f"TCP connection timeout for {addr}")
                    break

                if not data:
                    logger.info(f"TCP client {addr} disconnected (empty data)")
                    break

                raw_data = data.decode('utf-8', errors='replace').strip()
                if not raw_data:
                    continue

                try:
                    self.process_data(raw_data, addr)
                except Exception as e:
                    logger.error(f"TCP data processing error for {addr}: {e}", exc_info=True)

        except ConnectionResetError:
            logger.info(f"TCP connection reset by {addr}")
        except BrokenPipeError:
            logger.info(f"TCP connection broken pipe for {addr}")
        except Exception as e:
            logger.error(f"TCP connection error for {addr}: {e}", exc_info=True)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            logger.info(f"TCP connection closed for {addr}")

    def process_data(self, raw_data, client_addr=None):
        with self.app.app_context():
            user = User.query.get(self.user_id)
            if not user:
                logger.error(f"User {self.user_id} not found")
                return

            parsed = False
            error_msg = None
            client_ip = client_addr[0] if client_addr else None

            try:
                parsed_msg = parse_message(raw_data)
                parsed = True
                store_data(user.id, parsed_msg)

                try:
                    self.check_alarms(user.id, parsed_msg)
                except Exception as e:
                    logger.error(f"Alarm check error: {e}")

            except ValueError as e:
                error_msg = str(e)
                logger.warning(f"Failed to parse TCP data for user {self.user_id}: {error_msg}")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Database error for user {self.user_id}: {e}", exc_info=True)

            try:
                tcp_log = TcpLog(
                    port=user.id,
                    client_ip=client_ip,
                    direction='in',
                    content=raw_data[:2000] if raw_data else '',
                    status='success' if parsed else 'error',
                    error_message=error_msg
                )
                db.session.add(tcp_log)
                db.session.commit()
            except Exception as e:
                logger.error(f"Failed to save TCP log: {e}")
                db.session.rollback()


def store_data(user_id, parsed):
    try:
        device_info = parsed['device']
        device_name = device_info['name']
        # 兼容两种电压字段
        voltage = device_info.get('voltage')
        if voltage is None:
            voltage_mv = device_info.get('voltage_mv', 0)
            voltage = round(float(voltage_mv) / 1000.0, 2) if voltage_mv else 0.0
        else:
            voltage = float(voltage)
        now = datetime.utcnow()

        device = Device.query.filter_by(user_id=user_id, name=device_name).first()
        if not device:
            device = Device(
                user_id=user_id,
                name=device_name,
                voltage=voltage,
                is_online=True,
                last_seen=now,
                first_seen=now
            )
            db.session.add(device)
            db.session.flush()
        else:
            device.voltage = voltage
            device.is_online = True
            device.last_seen = now

        for ch_info in parsed['channels']:
            ch_name = ch_info['name']
            ch_online = ch_info['online']

            channel = Channel.query.filter_by(device_id=device.id, name=ch_name).first()
            if not channel:
                channel = Channel(
                    device_id=device.id,
                    name=ch_name,
                    is_online=ch_online,
                    first_seen=now,
                    last_seen=now
                )
                db.session.add(channel)
                db.session.flush()
            else:
                channel.is_online = ch_online
                channel.last_seen = now

            data_points = ch_info['data_points']
            if isinstance(data_points, dict):
                dp_iter = data_points.items()
            else:
                dp_iter = [(dp['name'], dp['value']) for dp in data_points]

            for dp_name, dp_value in dp_iter:
                if dp_value is None:
                    val = Decimal('0')
                elif isinstance(dp_value, Decimal):
                    val = dp_value
                else:
                    try:
                        val = Decimal(str(dp_value))
                    except (InvalidOperation, ValueError):
                        val = Decimal('0')

                dp = DataPoint.query.filter_by(
                    channel_id=channel.id, name=dp_name
                ).first()
                if not dp:
                    dp = DataPoint(
                        channel_id=channel.id,
                        name=dp_name,
                        value=val,
                        last_value=Decimal('0'),
                        last_updated=now,
                        update_count=1
                    )
                    db.session.add(dp)
                else:
                    dp.last_value = dp.value
                    dp.value = val
                    dp.last_updated = now
                    dp.update_count = (dp.update_count or 0) + 1

                hist = DataHistory(
                    data_point_id=dp.id,
                    device_id=device.id,
                    channel_id=channel.id,
                    value=val,
                    timestamp=now
                )
                db.session.add(hist)

        db.session.commit()

        with _tcp_stats_lock:
            _tcp_stats['total_messages'] += 1
            _tcp_stats['last_activity'] = datetime.utcnow()

        logger.info(f"Stored data for user {user_id}, device {device_name}")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to store data for user {user_id}: {e}", exc_info=True)
        raise


import asyncio
