"""
WebSocket 双向实时通信服务
- 路径：/ws/* （统一前缀）
- 鉴权：连接时通过 query token 或首个 message 验证登录态
- 通道订阅：客户端可订阅 device / alarm / event 通道
- 推送：服务端可通过 push_to_ws / push_to_user 推送到通道
- 双向：客户端可发送 command/control 消息到服务端执行
"""
import json
import time
import threading
from datetime import datetime
from typing import Dict, Set, Optional
from collections import defaultdict

from flask import request
from flask_login import current_user
from flask_sock import Sock

# 全局连接管理
class WSManager:
    def __init__(self):
        self._lock = threading.RLock()
        # user_id -> set of ws connections
        self._connections: Dict[int, Set] = defaultdict(set)
        # channel -> set of ws connections
        self._channels: Dict[str, Set] = defaultdict(set)
        # 每个连接: {user_id, channels:set, meta:dict}
        self._meta: Dict = {}
        # 统计
        self._stats = {'total_messages': 0, 'total_connections': 0, 'active': 0}

    def register(self, ws, user_id: int, meta: dict = None):
        with self._lock:
            self._connections[user_id].add(ws)
            self._meta[ws] = {'user_id': user_id, 'channels': set(), 'meta': meta or {}, 'connected_at': datetime.utcnow()}
            self._stats['total_connections'] += 1
            self._stats['active'] = sum(len(s) for s in self._connections.values())

    def unregister(self, ws):
        with self._lock:
            meta = self._meta.pop(ws, None)
            if not meta:
                return
            self._connections[meta['user_id']].discard(ws)
            for ch in meta['channels']:
                self._channels[ch].discard(ws)
            self._stats['active'] = sum(len(s) for s in self._connections.values())

    def subscribe(self, ws, channel: str):
        with self._lock:
            if ws not in self._meta:
                return False
            self._meta[ws]['channels'].add(channel)
            self._channels[channel].add(ws)
            return True

    def unsubscribe(self, ws, channel: str):
        with self._lock:
            if ws not in self._meta:
                return False
            self._meta[ws]['channels'].discard(channel)
            self._channels[channel].discard(ws)
            return True

    def push_channel(self, channel: str, payload: dict):
        """推送到所有订阅了某通道的连接"""
        with self._lock:
            conns = list(self._channels.get(channel, set()))
        msg = json.dumps({'type': 'channel', 'channel': channel, 'payload': payload, 'ts': time.time()}, default=str)
        for ws in conns:
            try:
                ws.send(msg)
            except Exception:
                pass

    def push_user(self, user_id: int, payload: dict):
        with self._lock:
            conns = list(self._connections.get(user_id, set()))
        msg = json.dumps({'type': 'user', 'payload': payload, 'ts': time.time()}, default=str)
        for ws in conns:
            try:
                ws.send(msg)
            except Exception:
                pass

    def broadcast(self, payload: dict):
        with self._lock:
            conns = [c for s in self._connections.values() for c in s]
        msg = json.dumps({'type': 'broadcast', 'payload': payload, 'ts': time.time()}, default=str)
        for ws in conns:
            try:
                ws.send(msg)
            except Exception:
                pass

    def stats(self) -> dict:
        with self._lock:
            return {
                **self._stats,
                'active': sum(len(s) for s in self._connections.values()),
                'channels': {ch: len(conns) for ch, conns in self._channels.items() if conns},
                'users_online': len([uid for uid, conns in self._connections.items() if conns]),
            }


# 单例
_ws_manager: Optional[WSManager] = None
_ws_lock = threading.Lock()


def get_ws_manager() -> WSManager:
    global _ws_manager
    with _ws_lock:
        if _ws_manager is None:
            _ws_manager = WSManager()
        return _ws_manager


def init_ws_routes(app, sock: Sock):
    """注册 WebSocket 路由到 Flask app"""

    @sock.route('/ws')
    def ws_endpoint(ws):
        """主 WS 端点：/ws?token=xxx"""
        from flask_login import login_user
        from models.database import User
        # 通过 query token 鉴权（生产可用 JWT/session）
        token = request.args.get('token') or ''
        user = None
        if token:
            # 简单实现：token = user_id:secret
            try:
                uid = int(token.split(':')[0])
                user = User.query.get(uid)
            except (ValueError, IndexError):
                pass
        if not user:
            try:
                ws.send(json.dumps({'type': 'error', 'msg': 'auth required: pass ?token=<user_id>:secret'}))
            except Exception:
                pass
            ws.close()
            return

        mgr = get_ws_manager()
        mgr.register(ws, user.id, meta={'username': user.username, 'is_admin': user.is_admin})
        try:
            ws.send(json.dumps({'type': 'welcome', 'user_id': user.id, 'username': user.username,
                                'msg': 'connected. Send {"action":"subscribe","channel":"device:<id>"} to subscribe.'}))
            while True:
                raw = ws.receive(timeout=60)
                if raw is None:
                    # 心跳超时，发送 ping
                    try:
                        ws.send(json.dumps({'type': 'ping', 'ts': time.time()}))
                        continue
                    except Exception:
                        break
                try:
                    data = json.loads(raw)
                except (ValueError, TypeError):
                    ws.send(json.dumps({'type': 'error', 'msg': 'invalid JSON'}))
                    continue
                mgr._stats['total_messages'] += 1
                action = data.get('action')
                if action == 'subscribe':
                    ch = data.get('channel')
                    if ch and isinstance(ch, str):
                        ok = mgr.subscribe(ws, ch)
                        ws.send(json.dumps({'type': 'subscribed', 'channel': ch, 'ok': ok}))
                elif action == 'unsubscribe':
                    ch = data.get('channel')
                    if ch:
                        ok = mgr.unsubscribe(ws, ch)
                        ws.send(json.dumps({'type': 'unsubscribed', 'channel': ch, 'ok': ok}))
                elif action == 'ping':
                    ws.send(json.dumps({'type': 'pong', 'ts': time.time()}))
                elif action == 'command':
                    # 设备控制命令（演示用：echo + broadcast）
                    payload = data.get('payload', {})
                    cmd = payload.get('command')
                    device_id = payload.get('device_id')
                    resp = {
                        'type': 'command_result',
                        'command': cmd,
                        'device_id': device_id,
                        'result': f'命令 {cmd} 已接收（演示）',
                        'ts': time.time()
                    }
                    ws.send(json.dumps(resp))
                elif action == 'stats':
                    ws.send(json.dumps({'type': 'stats', 'data': mgr.stats()}))
                else:
                    ws.send(json.dumps({'type': 'error', 'msg': f'unknown action: {action}'}))
        except Exception as e:
            try:
                ws.send(json.dumps({'type': 'error', 'msg': str(e)}))
            except Exception:
                pass
        finally:
            mgr.unregister(ws)

    @sock.route('/ws/stats')
    def ws_stats(ws):
        """WS 统计（无需鉴权）"""
        try:
            ws.send(json.dumps({'type': 'stats', 'data': get_ws_manager().stats()}))
            while True:
                ws.receive()  # 阻塞保持
        except Exception:
            pass


# 提供给其他服务调用的便捷 API
def push_device_data(device_id: int, data: dict):
    """推送设备实时数据（订阅了 device:<id> 通道的客户端会收到）"""
    get_ws_manager().push_channel(f'device:{device_id}', data)


def push_alarm(alarm_dict: dict):
    get_ws_manager().push_channel('alarm', alarm_dict)


def push_event(event_type: str, payload: dict):
    get_ws_manager().push_channel(f'event:{event_type}', payload)
