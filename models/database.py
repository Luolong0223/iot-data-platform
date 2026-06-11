from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    tcp_port = db.Column(db.Integer, unique=True, nullable=True)
    storage_enabled = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    devices = db.relationship('Device', back_populates='user', cascade='all, delete-orphan', lazy='dynamic')
    tcp_logs = db.relationship('TcpLog', back_populates='user', cascade='all, delete-orphan', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'is_admin': self.is_admin,
            'tcp_port': self.tcp_port,
            'storage_enabled': self.storage_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Device(db.Model):
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    voltage_mv = db.Column(db.Integer, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    location_name = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', back_populates='devices')
    channels = db.relationship('SlaveChannel', back_populates='device', cascade='all, delete-orphan', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'voltage_mv': self.voltage_mv,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'location_name': self.location_name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SlaveChannel(db.Model):
    __tablename__ = 'slave_channels'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    online = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    device = db.relationship('Device', back_populates='channels')
    data_points = db.relationship('DataPoint', back_populates='channel', cascade='all, delete-orphan', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'name': self.name,
            'online': self.online,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class DataPoint(db.Model):
    __tablename__ = 'data_points'

    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('slave_channels.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

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
    __tablename__ = 'tcp_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    raw_data = db.Column(db.Text, nullable=False)
    parsed = db.Column(db.Boolean, default=False, nullable=False)
    error_msg = db.Column(db.String(500), nullable=True)
    received_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', back_populates='tcp_logs')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'raw_data': self.raw_data,
            'parsed': self.parsed,
            'error_msg': self.error_msg,
            'received_at': self.received_at.isoformat() if self.received_at else None
        }


class AlarmRule(db.Model):
    __tablename__ = 'alarm_rules'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    device_name = db.Column(db.String(100), nullable=False)
    channel_name = db.Column(db.String(100), nullable=False)
    point_name = db.Column(db.String(100), nullable=False)
    condition = db.Column(db.String(10), nullable=False)  # 'gt', 'lt', 'eq'
    threshold = db.Column(db.Float, nullable=False)
    enabled = db.Column(db.Boolean, default=True, nullable=False)
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
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AlarmRecord(db.Model):
    __tablename__ = 'alarm_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rule_id = db.Column(db.Integer, db.ForeignKey('alarm_rules.id'), nullable=True)
    device_name = db.Column(db.String(100), nullable=False)
    channel_name = db.Column(db.String(100), nullable=False)
    point_name = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Float, nullable=False)
    threshold = db.Column(db.Float, nullable=False)
    condition = db.Column(db.String(10), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

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
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
