from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """用户表"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    tcp_port = db.Column(db.Integer, unique=True, nullable=True)
    storage_enabled = db.Column(db.Boolean, default=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    devices = db.relationship('Device', back_populates='user', cascade='all, delete-orphan', lazy='dynamic')
    tcp_logs = db.relationship('TcpLog', back_populates='user', cascade='all, delete-orphan', lazy='dynamic')
    login_logs = db.relationship('LoginLog', back_populates='user', cascade='all, delete-orphan', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'tcp_port': self.tcp_port,
            'storage_enabled': self.storage_enabled,
            'is_active': self.is_active,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'last_login_ip': self.last_login_ip,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class DeviceGroup(db.Model):
    """设备分组表"""
    __tablename__ = 'device_groups'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    color = db.Column(db.String(7), default='#3498db', nullable=False)  # 分组颜色
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref='device_groups')
    devices = db.relationship('Device', back_populates='group', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'sort_order': self.sort_order,
            'device_count': self.devices.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Device(db.Model):
    """设备表"""
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    group_id = db.Column(db.Integer, db.ForeignKey('device_groups.id'), nullable=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    device_type = db.Column(db.String(50), nullable=True)  # 设备类型
    voltage_mv = db.Column(db.Integer, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    location_name = db.Column(db.String(200), nullable=True)
    last_seen_at = db.Column(db.DateTime, nullable=True)  # 最后通信时间
    is_online = db.Column(db.Boolean, default=False, nullable=False)  # 在线状态
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', back_populates='devices')
    group = db.relationship('DeviceGroup', back_populates='devices')
    channels = db.relationship('SlaveChannel', back_populates='device', cascade='all, delete-orphan', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'group_id': self.group_id,
            'group_name': self.group.name if self.group else None,
            'name': self.name,
            'device_type': self.device_type,
            'voltage_mv': self.voltage_mv,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'location_name': self.location_name,
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None,
            'is_online': self.is_online,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SlaveChannel(db.Model):
    """从通道表"""
    __tablename__ = 'slave_channels'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    online = db.Column(db.Boolean, default=False, nullable=False)
    last_data_at = db.Column(db.DateTime, nullable=True)  # 最后数据时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    device = db.relationship('Device', back_populates='channels')
    data_points = db.relationship('DataPoint', back_populates='channel', cascade='all, delete-orphan', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'device_name': self.device.name if self.device else None,
            'name': self.name,
            'online': self.online,
            'last_data_at': self.last_data_at.isoformat() if self.last_data_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class DataPoint(db.Model):
    """数据点表"""
    __tablename__ = 'data_points'

    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('slave_channels.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    value = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 复合索引优化查询性能
    __table_args__ = (
        db.Index('idx_data_point_channel_name_time', 'channel_id', 'name', 'timestamp'),
        db.Index('idx_data_point_time_desc', timestamp.desc()),
    )

    channel = db.relationship('SlaveChannel', back_populates='data_points')

    def to_dict(self):
        return {
            'id': self.id,
            'channel_id': self.channel_id,
            'name': self.name,
            'value': self.value,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'device_name': self.channel.device.name if self.channel and self.channel.device else None,
            'channel_name': self.channel.name if self.channel else None
        }


class TcpLog(db.Model):
    """TCP日志表"""
    __tablename__ = 'tcp_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    raw_data = db.Column(db.Text, nullable=False)
    parsed = db.Column(db.Boolean, default=False, nullable=False, index=True)
    error_msg = db.Column(db.String(500), nullable=True)
    client_ip = db.Column(db.String(45), nullable=True)  # 客户端IP
    received_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship('User', back_populates='tcp_logs')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'raw_data': self.raw_data[:500] + '...' if len(self.raw_data) > 500 else self.raw_data,  # 截断显示
            'parsed': self.parsed,
            'error_msg': self.error_msg,
            'client_ip': self.client_ip,
            'received_at': self.received_at.isoformat() if self.received_at else None
        }


class LoginLog(db.Model):
    """登录日志表"""
    __tablename__ = 'login_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    username = db.Column(db.String(80), nullable=False, index=True)
    login_type = db.Column(db.String(20), nullable=False)  # login, logout, failed
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    success = db.Column(db.Boolean, default=True, nullable=False)
    failure_reason = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship('User', back_populates='login_logs')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'login_type': self.login_type,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent[:100] if self.user_agent else None,
            'success': self.success,
            'failure_reason': self.failure_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AlarmRule(db.Model):
    """报警规则表"""
    __tablename__ = 'alarm_rules'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    device_name = db.Column(db.String(100), nullable=False, index=True)
    channel_name = db.Column(db.String(100), nullable=False)
    point_name = db.Column(db.String(100), nullable=False)
    condition = db.Column(db.String(10), nullable=False)  # 'gt', 'lt', 'eq', 'gte', 'lte'
    threshold = db.Column(db.Float, nullable=False)
    severity = db.Column(db.String(20), default='warning', nullable=False)  # info, warning, critical
    notify_email = db.Column(db.Boolean, default=False, nullable=False)
    notify_sms = db.Column(db.Boolean, default=False, nullable=False)
    enabled = db.Column(db.Boolean, default=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref='alarm_rules')
    alarm_records = db.relationship('AlarmRecord', backref='rule', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'device_name': self.device_name,
            'channel_name': self.channel_name,
            'point_name': self.point_name,
            'condition': self.condition,
            'threshold': self.threshold,
            'severity': self.severity,
            'notify_email': self.notify_email,
            'notify_sms': self.notify_sms,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AlarmRecord(db.Model):
    """报警记录表"""
    __tablename__ = 'alarm_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('alarm_rules.id'), nullable=True, index=True)
    device_name = db.Column(db.String(100), nullable=False, index=True)
    channel_name = db.Column(db.String(100), nullable=False)
    point_name = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Float, nullable=False)
    threshold = db.Column(db.Float, nullable=False)
    condition = db.Column(db.String(10), nullable=False)
    severity = db.Column(db.String(20), default='warning', nullable=False)
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_handled = db.Column(db.Boolean, default=False, nullable=False)
    handled_by = db.Column(db.String(80), nullable=True)
    handled_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship('User', backref='alarm_records')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'rule_id': self.rule_id,
            'device_name': self.device_name,
            'channel_name': self.channel_name,
            'point_name': self.point_name,
            'value': self.value,
            'threshold': self.threshold,
            'condition': self.condition,
            'severity': self.severity,
            'message': self.message,
            'is_read': self.is_read,
            'is_handled': self.is_handled,
            'handled_by': self.handled_by,
            'handled_at': self.handled_at.isoformat() if self.handled_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SystemConfig(db.Model):
    """系统配置表"""
    __tablename__ = 'system_configs'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(500), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
