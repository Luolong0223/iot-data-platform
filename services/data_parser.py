import json
from datetime import datetime


def parse_tcp_data(raw_json):
    """
    Parse TCP JSON data format:
    {
      "device": {"name": "Collector-1", "voltage_mv": 3037},
      "s1": {"name": "Slave-1", "online": 1, "data": {"Data-1": 0.0000}},
      "s2": {"name": "Slave-2", "online": 1, "data": {"P1": 0.0000}}
    }

    Returns:
        dict with keys: device_info, channels (list of dicts)
        or raises ValueError on invalid format
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {str(e)}")

    if not isinstance(data, dict):
        raise ValueError("JSON must be an object")

    if 'device' not in data:
        raise ValueError("Missing 'device' field")

    device_info = data['device']
    if not isinstance(device_info, dict):
        raise ValueError("'device' must be an object")

    device_name = device_info.get('name')
    if not device_name:
        raise ValueError("Missing device.name")

    voltage_mv = device_info.get('voltage_mv')
    if voltage_mv is not None and not isinstance(voltage_mv, (int, float)):
        raise ValueError("device.voltage_mv must be a number")

    channels = []
    for key, value in data.items():
        if key == 'device':
            continue
        if not isinstance(value, dict):
            continue
        if 'name' not in value:
            continue

        channel_name = value.get('name')
        online = bool(value.get('online', 0))
        channel_data = value.get('data', {})
        if not isinstance(channel_data, dict):
            channel_data = {}

        data_points = []
        for point_name, point_value in channel_data.items():
            try:
                data_points.append({
                    'name': str(point_name),
                    'value': float(point_value)
                })
            except (ValueError, TypeError):
                continue

        channels.append({
            'key': key,
            'name': channel_name,
            'online': online,
            'data_points': data_points
        })

    return {
        'device_name': device_name,
        'voltage_mv': voltage_mv,
        'channels': channels
    }
