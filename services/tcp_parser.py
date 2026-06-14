"""
TCP 数据解析器 - 解析用户指定的报文格式
报文示例:
{
  "device": {"name": "Collector-1", "voltage_mv": 3037},
  "s1": {"name": "Slave-1", "online": 1, "data": {"Data-1": 0.0000}}
}
"""
import json
import logging
from datetime import datetime
from models.database import db, Device, Channel, DataPoint

logger = logging.getLogger(__name__)


class TcpParseError(Exception):
    """TCP 数据解析异常"""
    pass


def parse_message(raw: str) -> dict:
    """
    解析 TCP 报文
    返回: {device: {name, voltage_mv}, channels: [{name, online, data_points: {name: value}}]}
    抛 TcpParseError
    """
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError as e:
        raise TcpParseError(f"JSON 解析失败: {e}")

    if not isinstance(msg, dict):
        raise TcpParseError("报文必须是 JSON 对象")

    # device 字段是必须的
    device_info = msg.get('device')
    if not device_info or not isinstance(device_info, dict):
        raise TcpParseError("缺少 'device' 字段")

    device_name = device_info.get('name')
    if not device_name:
        raise TcpParseError("device.name 字段不能为空")

    voltage_mv = device_info.get('voltage_mv')

    # 找所有通道 (s1, s2, ... 或者任何非 device 字段)
    channels = []
    for key, val in msg.items():
        if key == 'device':
            continue
        if not isinstance(val, dict):
            continue
        ch_name = val.get('name', key)
        online = val.get('online', 1)
        if isinstance(online, str):
            online = 1 if online.lower() in ('1', 'true', 'online', 'yes') else 0
        data_points = val.get('data', {})
        if not isinstance(data_points, dict):
            data_points = {}
        # 也兼容 val 里的其他数值字段
        for k, v in list(val.items()):
            if k in ('name', 'online', 'data'):
                continue
            if isinstance(v, (int, float)):
                data_points[k] = v

        channels.append({
            'name': ch_name,
            'online': bool(online),
            'data_points': data_points
        })

    return {
        'device': {'name': device_name, 'voltage_mv': voltage_mv},
        'channels': channels
    }


def store_data(parsed: dict) -> dict:
    """
    存储解析后的数据到数据库
    返回: {device_id, channel_count, data_point_count}
    """
    device_info = parsed['device']
    device_name = device_info['name']
    voltage_mv = device_info.get('voltage_mv')

    now = datetime.now()

    # 1) 创建设备
    device = Device.query.filter_by(name=device_name).first()
    if not device:
        device = Device(
            name=device_name,
            voltage_mv=voltage_mv,
            is_online=True,
            first_seen=now,
            last_seen=now
        )
        db.session.add(device)
        db.session.flush()  # 拿到 device.id
    else:
        device.is_online = True
        device.last_seen = now
        if voltage_mv is not None:
            device.voltage_mv = voltage_mv

    # 2) 遍历通道
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
            db.session.flush()
        else:
            channel.is_online = ch_online
            channel.last_seen = now

        channel_count += 1
        channel_ids.append(channel.id)

        # 3) 写数据点
        for dp_name, dp_value in ch_info['data_points'].items():
            try:
                value = float(dp_value)
            except (TypeError, ValueError):
                continue
            dp = DataPoint(
                channel_id=channel.id,
                name=dp_name,
                value=value,
                timestamp=now
            )
            db.session.add(dp)
            dp_count += 1

    # 4) 把离线通道(没在本次报文中出现的) 标记为离线
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


def parse_and_store(raw: str) -> dict:
    """解析并存储,异常抛 TcpParseError"""
    parsed = parse_message(raw)
    return store_data(parsed)
