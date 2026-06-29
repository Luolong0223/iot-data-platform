"""
TCP 数据解析器 - 解析设备上报的 JSON 数据
"""
import json
import logging
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """数据解析异常"""
    pass


def parse_tcp_data(raw_data: str) -> dict:
    """
    解析 TCP JSON 数据
    支持两种电压字段:
      - voltage: 伏特浮点数 (如 4.04)
      - voltage_mv: 毫伏整数 (如 4040)
    返回: {device_name, voltage, channels: [{name, online, data_points: [{name, value}]}]}
    """
    try:
        msg = json.loads(raw_data, parse_float=Decimal)
    except json.JSONDecodeError as e:
        raise ParseError(f"JSON 解析失败: {e}")

    if not isinstance(msg, dict):
        raise ParseError("数据必须是 JSON 对象")

    device_info = msg.get('device')
    if not device_info or not isinstance(device_info, dict):
        raise ParseError("缺少 'device' 字段")

    device_name = device_info.get('name')
    if not device_name:
        raise ParseError("device.name 不能为空")

    # 兼容两种电压字段
    voltage = device_info.get('voltage')
    if voltage is None:
        # 兼容旧格式 voltage_mv (毫伏)
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
        for k, v in val.items():
            if k in ('name', 'online', 'data'):
                continue
            if isinstance(v, (int, float, Decimal)):
                data_dict[k] = v

        data_points = []
        for k, v in data_dict.items():
            if v is None:
                val_dp = Decimal('0')
            elif isinstance(v, Decimal):
                val_dp = v
            else:
                try:
                    val_dp = Decimal(str(v))
                except (InvalidOperation, ValueError):
                    val_dp = Decimal('0')
            data_points.append({'name': k, 'value': val_dp})

        channels.append({
            'name': ch_name,
            'online': bool(online),
            'data_points': data_points
        })

    return {
        'device_name': device_name,
        'voltage': voltage,
        'channels': channels
    }
