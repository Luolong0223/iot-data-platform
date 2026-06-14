"""协议适配器 - Modbus / HTTP 数据接入

支持：
  - Modbus TCP 主动轮询采集器
  - HTTP 数据接收端点（已有 TCP + JSON）
  - 协议解析器注册接口
"""
import asyncio
import struct
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required

try:
    from pymodbus.client import ModbusTcpClient as _ModbusClient
    MODBUS_AVAILABLE = True
except ImportError:
    MODBUS_AVAILABLE = False


def parse_holding_register(registers, decoder='INT16', scale=1.0, offset=0):
    """解析 Modbus 保持寄存器"""
    values = []
    for reg in registers:
        if decoder == 'INT16':
            val = struct.unpack('>h', struct.pack('>H', reg))[0]
        elif decoder == 'UINT16':
            val = reg
        elif decoder == 'INT32':
            val = reg
        else:
            val = reg
        val = val * scale + offset
        values.append(round(val, 4))
    return values


class ModbusPoller:
    """Modbus TCP 轮询采集器"""

    def __init__(self, host, port=502, unit_id=1, registers=None, interval=10):
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.registers = registers or []  # [{'address':0, 'count':1, 'name':'T', 'decoder':'INT16', 'scale':0.1}]
        self.interval = interval
        self.running = False
        self.task = None
        self.last_data = {}

    async def poll_once(self, on_data):
        if not MODBUS_AVAILABLE:
            return False, 'pymodbus 未安装'
        try:
            client = _ModbusClient(self.host, port=self.port, timeout=5)
            if not client.connect():
                return False, f'无法连接 {self.host}:{self.port}'

            collected = {'timestamp': datetime.utcnow().isoformat()}
            for reg in self.registers:
                resp = client.read_holding_registers(
                    address=reg['address'],
                    count=reg.get('count', 1),
                    slave=self.unit_id
                )
                if not resp.isError():
                    values = parse_holding_register(
                        resp.registers,
                        decoder=reg.get('decoder', 'INT16'),
                        scale=reg.get('scale', 1.0),
                        offset=reg.get('offset', 0)
                    )
                    if reg.get('count', 1) == 1:
                        collected[reg['name']] = values[0]
                    else:
                        collected[reg['name']] = values
                else:
                    collected[reg['name']] = None

            client.close()
            self.last_data = collected
            if on_data:
                await on_data(collected)
            return True, None
        except Exception as e:
            return False, str(e)[:200]

    async def _run_loop(self, on_data):
        while self.running:
            ok, err = await self.poll_once(on_data)
            if not ok:
                print(f'[modbus:{self.host}:{self.port}] {err}')
            await asyncio.sleep(self.interval)

    def start(self, on_data):
        if self.running:
            return False
        self.running = True
        self.task = asyncio.create_task(self._run_loop(on_data))
        return True

    def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()


# 简易 HTTP 数据接收端点 - 用于其他系统推送数据
def http_receiver_handler():
    """处理 HTTP POST 推送的数据
    格式: {"device_key": "xxx", "data": {"point1": 1.0, "point2": 2.0}}
    """
    from flask import request, jsonify
    from models.database import db, Device, SlaveChannel, DataPoint
    from flask_login import current_user
    from datetime import datetime
    from routes.realtime import push_to_user

    payload = request.get_json(force=True, silent=True) or {}
    device_key = payload.get('device_key') or payload.get('deviceKey')
    if not device_key:
        return jsonify({'success': False, 'error': '缺少 device_key'}), 400

    user_id = payload.get('user_id', current_user.id if current_user.is_authenticated else None)
    if not user_id:
        return jsonify({'success': False, 'error': '未授权'}), 401

    device = Device.query.filter_by(device_key=device_key, user_id=user_id).first()
    if not device:
        return jsonify({'success': False, 'error': '设备不存在'}), 404

    data = payload.get('data', {})
    if not isinstance(data, dict):
        return jsonify({'success': False, 'error': 'data 格式错误'}), 400

    # 默认通道：default
    channel = SlaveChannel.query.filter_by(device_id=device.id, name='default').first()
    if not channel:
        channel = SlaveChannel(device_id=device.id, name='default', online=True)
        db.session.add(channel)
        db.session.flush()

    saved_count = 0
    for key, val in data.items():
        try:
            value = float(val)
        except (TypeError, ValueError):
            continue
        if device.storage_enabled:
            dp = DataPoint(channel_id=channel.id, name=key, value=value, timestamp=datetime.utcnow())
            db.session.add(dp)
            saved_count += 1

    device.is_online = True
    device.last_seen_at = datetime.utcnow()
    db.session.commit()

    # 推送到 SSE
    push_to_user(user_id, {
        'type': 'data',
        'timestamp': datetime.utcnow().isoformat(),
        'data': {
            'device_name': device.name,
            'device_key': device_key,
            'channel_name': channel.name,
            'data_points': data,
            'source': 'http'
        }
    })

    return jsonify({'success': True, 'saved': saved_count})


# 协议解析器注册表
PARSERS = {}


def register_parser(name, func):
    """注册自定义协议解析器
    func(data: bytes) -> dict
    """
    PARSERS[name] = func


def get_parser(name):
    return PARSERS.get(name)
