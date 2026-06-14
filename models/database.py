"""
IoT 数据平台 - 数据模型
简化版本：只保留核心功能所需的模型
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ============= 用户与权限 =============

class User(UserMixin, db.Model):
    """用户表"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M') if self.last_login else None
        }


# ============= 设备数据 =============

class DeviceCategory(db.Model):
    """设备分类（树形结构）"""
    __tablename__ = 'device_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('device_categories.id', ondelete='CASCADE'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 自引用关系
    children = db.relationship('DeviceCategory', backref=db.backref('parent', remote_side=[id]),
                                cascade='all, delete-orphan')
    devices = db.relationship('Device', backref='category', lazy='dynamic')

    def to_dict(self, with_children=True):
        d = {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'sort_order': self.sort_order,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None
        }
        if with_children:
            d['children'] = [c.to_dict() for c in sorted(self.children, key=lambda x: x.sort_order)]
        return d


class Device(db.Model):
    """设备表
    TCP 报文 device.name 字段对应此表的 name 字段
    voltage_mv 字段存储设备当前电压
    """
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    custom_name = db.Column(db.String(100), nullable=True)  # 用户自定义名称
    voltage_mv = db.Column(db.Integer, default=0)  # 电压(mV)

    category_id = db.Column(db.Integer, db.ForeignKey('device_categories.id', ondelete='SET NULL'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    is_online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, nullable=True)  # 最后接收数据时间
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)  # 首次发现时间
    total_packets = db.Column(db.Integer, default=0)  # 累计接收报文数

    channels = db.relationship('Channel', backref='device', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self, with_channels=False):
        d = {
            'id': self.id,
            'name': self.name,
            'custom_name': self.custom_name or self.name,
            'display_name': self.custom_name or self.name,
            'voltage_mv': self.voltage_mv,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'is_online': self.is_online,
            'last_seen': self.last_seen.strftime('%Y-%m-%d %H:%M:%S') if self.last_seen else None,
            'first_seen': self.first_seen.strftime('%Y-%m-%d %H:%M:%S') if self.first_seen else None,
            'total_packets': self.total_packets,
            'channel_count': self.channels.count()
        }
        if with_channels:
            d['channels'] = [c.to_dict() for c in self.channels]
        return d


class Channel(db.Model):
    """通道表
    TCP 报文 s1.name 字段对应此表的 name 字段
    online 字段存储通道在线状态
    """
    __tablename__ = 'channels'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False, index=True)  # 如 s1, s2
    is_online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, nullable=True)
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)

    data_points = db.relationship('DataPoint', backref='channel', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('device_id', 'name', name='uq_channel_device_name'),
    )

    def to_dict(self, with_data_points=False):
        d = {
            'id': self.id,
            'device_id': self.device_id,
            'name': self.name,
            'is_online': self.is_online,
            'last_seen': self.last_seen.strftime('%Y-%m-%d %H:%M:%S') if self.last_seen else None,
            'data_point_count': self.data_points.count()
        }
        if with_data_points:
            d['data_points'] = [dp.to_dict() for dp in self.data_points]
        return d


class DataPoint(db.Model):
    """数据点表
    TCP 报文 s1.data.Data-1 字段对应此表：
      - name 字段 = "Data-1"
      - value 字段 = 0.0000
    """
    __tablename__ = 'data_points'

    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False, index=True)  # 如 Data-1, P1
    value = db.Column(db.Float, default=0.0)  # 最新值
    last_value = db.Column(db.Float, default=0.0)  # 上一次值
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    update_count = db.Column(db.Integer, default=0)  # 累计更新次数

    __table_args__ = (
        db.UniqueConstraint('channel_id', 'name', name='uq_dp_channel_name'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'channel_id': self.channel_id,
            'name': self.name,
            'value': self.value,
            'last_value': self.last_value,
            'last_updated': self.last_updated.strftime('%Y-%m-%d %H:%M:%S') if self.last_updated else None,
            'update_count': self.update_count
        }


class DataHistory(db.Model):
    """数据历史记录表 - 存储每个数据点的所有历史值"""
    __tablename__ = 'data_history'

    id = db.Column(db.Integer, primary_key=True)
    data_point_id = db.Column(db.Integer, db.ForeignKey('data_points.id', ondelete='CASCADE'), nullable=False, index=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False, index=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id', ondelete='CASCADE'), nullable=False, index=True)
    value = db.Column(db.Float, default=0.0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'data_point_id': self.data_point_id,
            'value': self.value,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else None
        }


# ============= 仪表盘配置 =============

class DashboardWidget(db.Model):
    """仪表盘显示项 - 用户选择要在仪表盘显示哪些数据点"""
    __tablename__ = 'dashboard_widgets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id', ondelete='CASCADE'), nullable=False)
    data_point_id = db.Column(db.Integer, db.ForeignKey('data_points.id', ondelete='CASCADE'), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    is_visible = db.Column(db.Boolean, default=True)
    color = db.Column(db.String(20), default='#3b82f6')  # 显示颜色
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    data_point = db.relationship('DataPoint', backref='widgets')

    def to_dict(self):
        dp = self.data_point
        ch = dp.channel if dp else None
        dev = ch.device if ch else None
        return {
            'id': self.id,
            'device_id': self.device_id,
            'device_name': dev.custom_name or dev.name if dev else '?',
            'channel_id': self.channel_id,
            'channel_name': ch.name if ch else '?',
            'data_point_id': self.data_point_id,
            'data_point_name': dp.name if dp else '?',
            'current_value': dp.value if dp else 0,
            'last_updated': dp.last_updated.strftime('%Y-%m-%d %H:%M:%S') if dp and dp.last_updated else None,
            'sort_order': self.sort_order,
            'is_visible': self.is_visible,
            'color': self.color
        }


# ============= TCP 服务 =============

class TcpServerConfig(db.Model):
    """TCP 监听端口配置"""
    __tablename__ = 'tcp_server_configs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # 端口名称
    port = db.Column(db.Integer, nullable=False, unique=True)
    host = db.Column(db.String(50), default='0.0.0.0')
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_started = db.Column(db.DateTime, nullable=True)
    total_connections = db.Column(db.Integer, default=0)
    total_messages = db.Column(db.Integer, default=0)
    error_count = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'port': self.port,
            'host': self.host,
            'is_active': self.is_active,
            'description': self.description,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'last_started': self.last_started.strftime('%Y-%m-%d %H:%M:%S') if self.last_started else None,
            'total_connections': self.total_connections,
            'total_messages': self.total_messages,
            'error_count': self.error_count
        }


class TcpLog(db.Model):
    """TCP 通信日志"""
    __tablename__ = 'tcp_logs'

    id = db.Column(db.Integer, primary_key=True)
    port = db.Column(db.Integer, nullable=False, index=True)
    client_ip = db.Column(db.String(50), nullable=True)
    direction = db.Column(db.String(10))  # 'in' / 'out'
    content = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='success')  # 'success' / 'error'
    error_message = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'port': self.port,
            'client_ip': self.client_ip,
            'direction': self.direction,
            'content': (self.content[:200] + '...') if self.content and len(self.content) > 200 else self.content,
            'status': self.status,
            'error_message': self.error_message,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else None
        }


# ============= 系统设置 =============

class SystemConfig(db.Model):
    """系统配置（键值对）"""
    __tablename__ = 'system_configs'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


class LoginLog(db.Model):
    """登录日志"""
    __tablename__ = 'login_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    username = db.Column(db.String(80), nullable=True)
    ip = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='success')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'ip': self.ip,
            'status': self.status,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else None
        }
