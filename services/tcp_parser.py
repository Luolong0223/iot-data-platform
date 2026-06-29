"""
TCP 数据解析器 - 解析设备上报的 JSON 报文
"""
import json
import logging
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


class TcpParseError(Exception):
    """TCP 数据解析异常"""
    pass


def parse_message(raw: str) -> dict:
    """
    解析 TCP 报文
    支持两种电压字段: voltage (V) 或 voltage_mv (mV)
    返回: {device: {name, voltage}, channels: [{name, online, data_points: [{name, value}]}]}
    """
    try:
        msg = json.loads(raw, parse_float=Decimal)
    except json.JSONDecodeError as e:
        raise TcpParseError(f"JSON 解析失败: {e}")

    if not isinstance(msg, dict):
        raise TcpParseError("报文必须是 JSON 对象")

    device_info = msg.get('device')
    if not device_info or not isinstance(device_info, dict):
        raise TcpParseError("缺少 'device' 字段")

    device_name = device_info.get('name')
    if not device_name:
        raise TcpParseError("device.name 字段不能为空")

    # 兼容两种电压字段
    voltage = device_info.get('voltage')
    if voltage is None:
        voltage_mv = device_info.get('voltage_mv', 0)
        voltage = round(float(voltage_mv) / 1000.0, 2) if voltage_mv else 0.0
    else:
        voltage = float(voltage)

    channels = []
    for key, val in msg.items():
        if key == 'device':
            continue
        if not isinstance(val, dict):
            continue

        ch_name = val.get('name', key)
        online = val.get('online', 1)
        if isinstance(online, str):
            online = 1 if online.lower() in ('1', 'true', 'online') else 0

        data_dict = val.get('data', {})
        if not isinstance(data_dict, dict):
            data_dict = {}

        # 兼容通道内的其他数值字段
        for k, v in list(val.items()):
            if k in ('name', 'online', 'data'):
                continue
            if isinstance(v, (int, float, Decimal)):
                data_dict[k] = v

        data_points = []
        for k, v in data_dict.items():
            if v is None:
                val = Decimal('0')
            elif isinstance(v, Decimal):
                val = v
            else:
                try:
                    val = Decimal(str(v))
                except (InvalidOperation, ValueError):
                    val = Decimal('0')
            data_points.append({'name': k, 'value': val})

        channels.append({
            'name': ch_name,
            'online': bool(online),
            'data_points': data_points
        })

    return {
        'device': {'name': device_name, 'voltage': voltage},
        'channels': channels
    }


def store_data(parsed: dict, user_id: int = None) -> dict:
    """
    存储解析后的数据到数据库
    返回: {device_id, device_name, channel_count, data_point_count}
    """
    from datetime import datetime
    from models.database import db, Device, Channel, DataPoint, DataHistory, User

    device_info = parsed['device']
    device_name = device_info['name']
    voltage = device_info.get('voltage', 0.0)

    now = datetime.utcnow()

    # 查找设备
    if user_id:
        device = Device.query.filter_by(user_id=user_id, name=device_name).first()
    else:
        device = Device.query.filter_by(name=device_name).first()

    if not device:
        # 找到 owner
        if user_id:
            owner_id = user_id
        else:
            owner = User.query.filter_by(is_admin=True).order_by(User.id).first()
            if not owner:
                owner = User.query.order_by(User.id).first()
            owner_id = owner.id if owner else 1

        device = Device(
            user_id=owner_id,
            name=device_name,
            voltage=voltage,
            is_online=True,
            first_seen=now,
            last_seen=now
        )
        db.session.add(device)
    else:
        device.is_online = True
        device.last_seen = now
        device.voltage = voltage
        device.total_packets = (device.total_packets or 0) + 1
    db.session.flush()

    # 遍历通道
    channel_count = 0
    dp_count = 0
    channel_ids = []

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
        else:
            channel.is_online = ch_online
            channel.last_seen = now
        db.session.flush()

        channel_count += 1
        channel_ids.append(channel.id)

        # 写数据点
        for dp_info in ch_info['data_points']:
            dp_name = dp_info['name']
            dp_value = dp_info['value']

            dp = DataPoint.query.filter_by(
                channel_id=channel.id, name=dp_name
            ).first()

            if dp:
                dp.last_value = dp.value
                dp.value = dp_value
                dp.last_updated = now
                dp.update_count = (dp.update_count or 0) + 1
            else:
                dp = DataPoint(
                    channel_id=channel.id,
                    name=dp_name,
                    value=dp_value,
                    last_value=0.0,
                    last_updated=now,
                    update_count=1
                )
                db.session.add(dp)
            db.session.flush()

            # 写入历史
            hist = DataHistory(
                data_point_id=dp.id,
                device_id=device.id,
                channel_id=channel.id,
                value=dp_value,
                timestamp=now
            )
            db.session.add(hist)
            dp_count += 1

    # 标记离线通道
    if channel_ids:
        offline_channels = Channel.query.filter(
            Channel.device_id == device.id,
            ~Channel.id.in_(channel_ids)
        ).all()
        for oc in offline_channels:
            oc.is_online = False

    db.session.commit()

    return {
        'device_id': device.id,
        'device_name': device.name,
        'channel_count': channel_count,
        'data_point_count': dp_count
    }


def parse_and_store(raw: str, user_id: int = None) -> dict:
    """解析并存储"""
    parsed = parse_message(raw)
    return store_data(parsed, user_id)
