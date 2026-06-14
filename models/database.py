from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, Float, JSON
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone

db = SQLAlchemy()


# 获取上海时间（UTC+8）
def _now():
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))


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
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

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


class ScreenSelectedPoint(db.Model):
    """用户大屏选定的数据点（持久化保存）"""
    __tablename__ = 'screen_selected_points'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    device_id = db.Column(db.Integer, nullable=False)
    device_name = db.Column(db.String(100), nullable=False)
    channel_id = db.Column(db.Integer, nullable=False)
    channel_name = db.Column(db.String(100), nullable=False)
    point_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'device_id', 'channel_id', 'point_name', name='uq_user_screen_point'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'device_id': self.device_id,
            'device_name': self.device_name,
            'channel_id': self.channel_id,
            'channel_name': self.channel_name,
            'point_name': self.point_name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Project(db.Model):
    """项目表（第一层级）"""
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    color = db.Column(db.String(7), default='#3498db', nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now, nullable=False)

    user = db.relationship('User', backref='projects')
    groups = db.relationship('DeviceGroup', back_populates='project', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'location': self.location,
            'color': self.color,
            'sort_order': self.sort_order,
            'group_count': self.groups.count(),
            'device_count': sum(g.devices.count() for g in self.groups),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class DeviceGroup(db.Model):
    """设备分组表（第二层级）"""
    __tablename__ = 'device_groups'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('device_groups.id'), nullable=True)  # 支持多级分组
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    color = db.Column(db.String(7), default='#3498db', nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now, nullable=False)

    user = db.relationship('User', backref='device_groups')
    project = db.relationship('Project', back_populates='groups')
    parent = db.relationship('DeviceGroup', remote_side=[id], backref='children')
    devices = db.relationship('Device', back_populates='group', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'project_id': self.project_id,
            'project_name': self.project.name if self.project else None,
            'parent_id': self.parent_id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'sort_order': self.sort_order,
            'device_count': self.devices.count(),
            'children_count': len(self.children) if self.children else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Device(db.Model):
    """设备表（第三层级）"""
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True, index=True)
    group_id = db.Column(db.Integer, db.ForeignKey('device_groups.id'), nullable=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    device_type = db.Column(db.String(50), nullable=True)
    device_key = db.Column(db.String(64), nullable=True, unique=True)  # 设备密钥
    voltage_mv = db.Column(db.Integer, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    location_name = db.Column(db.String(200), nullable=True)
    firmware_version = db.Column(db.String(32), nullable=True)  # 固件版本
    ip_address = db.Column(db.String(45), nullable=True)  # IP地址
    last_seen_at = db.Column(db.DateTime, nullable=True)
    is_online = db.Column(db.Boolean, default=False, nullable=False)
    storage_enabled = db.Column(db.Boolean, default=True, nullable=False)  # 是否存储数据
    maintenance_interval = db.Column(db.Integer, default=30)  # 维护周期（天）
    last_maintenance_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

    user = db.relationship('User', back_populates='devices')
    project = db.relationship('Project', backref='devices')
    group = db.relationship('DeviceGroup', back_populates='devices')
    channels = db.relationship('SlaveChannel', back_populates='device', cascade='all, delete-orphan', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'project_id': self.project_id,
            'project_name': self.project.name if self.project else None,
            'group_id': self.group_id,
            'group_name': self.group.name if self.group else None,
            'name': self.name,
            'device_type': self.device_type,
            'device_key': self.device_key,
            'voltage_mv': self.voltage_mv,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'location_name': self.location_name,
            'firmware_version': self.firmware_version,
            'ip_address': self.ip_address,
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None,
            'is_online': self.is_online,
            'storage_enabled': self.storage_enabled,
            'channel_count': self.channels.count(),
            'data_count': sum(c.data_points.count() for c in self.channels),
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
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

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
    timestamp = db.Column(db.DateTime, default=_now, nullable=False, index=True)

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
    received_at = db.Column(db.DateTime, default=_now, nullable=False, index=True)

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
    created_at = db.Column(db.DateTime, default=_now, nullable=False, index=True)

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
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

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
    created_at = db.Column(db.DateTime, default=_now, nullable=False, index=True)

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
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class NotificationConfig(db.Model):
    """通知配置表"""
    __tablename__ = 'notification_configs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    notify_type = db.Column(db.String(20), nullable=False)  # email, dingtalk, wechat
    name = db.Column(db.String(100), nullable=False)
    config = db.Column(db.Text, nullable=False)  # JSON格式的配置
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

    user = db.relationship('User', backref='notification_configs')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'notify_type': self.notify_type,
            'name': self.name,
            'config': self.config,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ============================================================
# v5.0 新增模型：设备影子/标签/审计/消息/协议/命令
# ============================================================

class DeviceShadow(db.Model):
    """设备影子：设备的虚拟状态（期望状态/报告状态）"""
    __tablename__ = 'device_shadows'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # 期望状态（云端 → 设备）
    desired_state = db.Column(db.Text, nullable=True)
    desired_version = db.Column(db.Integer, default=1, nullable=False)
    desired_updated_at = db.Column(db.DateTime, nullable=True)
    
    # 报告状态（设备 → 云端）
    reported_state = db.Column(db.Text, nullable=True)
    reported_version = db.Column(db.Integer, default=1, nullable=False)
    reported_updated_at = db.Column(db.DateTime, nullable=True)
    
    # 同步状态: pending/syncing/synced/failed
    sync_status = db.Column(db.String(16), default='pending', nullable=False, index=True)
    last_sync_at = db.Column(db.DateTime, nullable=True)
    sync_error = db.Column(db.String(500), nullable=True)
    
    # 在线状态
    is_online = db.Column(db.Boolean, default=False, nullable=False)
    
    # 元信息（JSON）：包含最新数据点摘要
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now, nullable=False)

    device = db.relationship('Device', backref=db.backref('shadow', uselist=False, cascade='all, delete-orphan'))
    user = db.relationship('User', backref='device_shadows')

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'device_id': self.device_id,
            'device_name': self.device.name if self.device else None,
            'desired_state': json.loads(self.desired_state) if self.desired_state else {},
            'desired_version': self.desired_version,
            'desired_updated_at': self.desired_updated_at.isoformat() if self.desired_updated_at else None,
            'reported_state': json.loads(self.reported_state) if self.reported_state else {},
            'reported_version': self.reported_version,
            'reported_updated_at': self.reported_updated_at.isoformat() if self.reported_updated_at else None,
            'sync_status': self.sync_status,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'sync_error': self.sync_error,
            'is_online': self.is_online,
            'metadata': json.loads(self.metadata_json) if self.metadata_json else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class DeviceTag(db.Model):
    """设备标签"""
    __tablename__ = 'device_tags'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(64), nullable=False)
    color = db.Column(db.String(16), default='#1890ff', nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='uq_device_tag_user_name'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'color': self.color,
            'description': self.description,
            'device_count': db.session.query(DeviceTagMapping).filter_by(tag_id=self.id).count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class DeviceTagMapping(db.Model):
    """设备-标签多对多关联"""
    __tablename__ = 'device_tag_mappings'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False, index=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('device_tags.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('device_id', 'tag_id', name='uq_device_tag_mapping'),
    )


class DeviceCommand(db.Model):
    """下发到设备的命令（云端 → 设备）"""
    __tablename__ = 'device_commands'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False, index=True)
    command = db.Column(db.String(64), nullable=False)
    payload = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(16), default='pending', nullable=False)  # pending/sent/ack/failed
    result = db.Column(db.Text, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    ack_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'command': self.command,
            'payload': self.payload,
            'status': self.status,
            'result': self.result,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'ack_at': self.ack_at.isoformat() if self.ack_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ProtocolAdapter(db.Model):
    """协议适配器（Modbus / MQTT / HTTP / 自定义）"""
    __tablename__ = 'protocol_adapters'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(64), nullable=False)
    protocol = db.Column(db.String(32), nullable=False)  # modbus/mqtt/http/custom
    config = db.Column(db.Text, nullable=True)  # JSON: 协议参数
    codec = db.Column(db.Text, nullable=True)  # JSON: 编解码脚本路径/规则
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    last_run_at = db.Column(db.DateTime, nullable=True)
    last_status = db.Column(db.String(16), nullable=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'protocol': self.protocol,
            'config': json.loads(self.config) if self.config else {},
            'codec': json.loads(self.codec) if self.codec else {},
            'enabled': self.enabled,
            'last_run_at': self.last_run_at.isoformat() if self.last_run_at else None,
            'last_status': self.last_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SystemMessage(db.Model):
    """系统消息（站内信/通知）"""
    __tablename__ = 'system_messages'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(128), nullable=False)
    content = db.Column(db.Text, nullable=False)
    level = db.Column(db.String(16), default='info', nullable=False)  # info/warn/error/success
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    link = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'content': self.content,
            'level': self.level,
            'is_read': self.is_read,
            'link': self.link,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AuditLog(db.Model):
    """操作审计日志"""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    username = db.Column(db.String(80), nullable=True)
    action = db.Column(db.String(64), nullable=False, index=True)  # login/logout/create/update/delete/export/import/send_cmd
    resource = db.Column(db.String(64), nullable=True)  # 资源类型
    resource_id = db.Column(db.String(64), nullable=True)
    detail = db.Column(db.Text, nullable=True)
    ip = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(16), default='success', nullable=False)
    created_at = db.Column(db.DateTime, default=_now, nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'action': self.action,
            'resource': self.resource,
            'resource_id': self.resource_id,
            'detail': self.detail,
            'ip': self.ip,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class NotificationLog(db.Model):
    """通知发送日志"""
    __tablename__ = 'notification_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    channel = db.Column(db.String(32), nullable=False)  # email/dingtalk/wechat/webhook
    target = db.Column(db.String(255), nullable=True)  # 邮箱地址 / webhook URL
    subject = db.Column(db.String(255), nullable=True)
    content = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(16), nullable=False)  # success/failed
    error = db.Column(db.Text, nullable=True)
    trigger_source = db.Column(db.String(64), nullable=True)  # 告警ID/规则ID等
    sent_at = db.Column(db.DateTime, default=_now, nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'channel': self.channel,
            'target': self.target,
            'subject': self.subject,
            'status': self.status,
            'error': self.error,
            'trigger_source': self.trigger_source,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None
        }


class ReportTask(db.Model):
    """报表任务（每日/每周/每月自动生成）"""
    __tablename__ = 'report_tasks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    type = db.Column(db.String(32), nullable=False)  # daily/weekly/monthly
    schedule_time = db.Column(db.String(16), default='08:00', nullable=False)  # HH:MM
    config = db.Column(db.Text, nullable=True)  # JSON: 报表配置
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    last_run_at = db.Column(db.DateTime, nullable=True)
    last_status = db.Column(db.String(16), nullable=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'type': self.type,
            'schedule_time': self.schedule_time,
            'config': json.loads(self.config) if self.config else {},
            'enabled': self.enabled,
            'last_run_at': self.last_run_at.isoformat() if self.last_run_at else None,
            'last_status': self.last_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ========================================================================
# RBAC 角色权限系统 (Task 4)
# ========================================================================

class Role(db.Model):
    """角色 - 权限集合的容器"""
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    name = db.Column(db.String(64), nullable=False)
    code = db.Column(db.String(64), nullable=False, index=True)
    description = db.Column(db.String(255))
    is_system = db.Column(db.Boolean, default=False)  # 系统内置角色不可删除
    is_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    user = db.relationship('User', backref='roles')
    role_permissions = db.relationship('RolePermission', back_populates='role', cascade='all, delete-orphan', lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'is_system': self.is_system,
            'is_enabled': self.is_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'permissions': [rp.permission.to_dict() for rp in self.role_permissions if rp.permission]
        }


class Permission(db.Model):
    """权限 - 资源+操作的最小单位"""
    __tablename__ = 'permissions'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(128), unique=True, nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    resource = db.Column(db.String(64), nullable=False, index=True)  # device/alarm/user/...
    action = db.Column(db.String(32), nullable=False)  # read/write/delete/admin
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

    role_permissions = db.relationship('RolePermission', back_populates='permission', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'resource': self.resource,
            'action': self.action,
            'description': self.description
        }


class RolePermission(db.Model):
    """角色-权限关联"""
    __tablename__ = 'role_permissions'

    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

    role = db.relationship('Role', back_populates='role_permissions')
    permission = db.relationship('Permission', back_populates='role_permissions')


class UserRole(db.Model):
    """用户-角色关联（一个用户可拥有多个角色）"""
    __tablename__ = 'user_roles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

    user = db.relationship('User', backref='user_roles')
    role = db.relationship('Role', backref='user_roles')


# ========================================================================
# OTA 固件升级
# ========================================================================

class Firmware(db.Model):
    """固件包"""
    __tablename__ = 'firmwares'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    version = db.Column(db.String(64), nullable=False)
    hardware_model = db.Column(db.String(64), nullable=True, index=True)
    file_path = db.Column(db.String(512), nullable=False)  # 相对于 instance/firmwares/ 或绝对路径
    file_size = db.Column(db.BigInteger, default=0)
    checksum = db.Column(db.String(128), nullable=True)  # md5/sha256
    description = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

    user = db.relationship('User', backref='firmwares')
    tasks = db.relationship('OtaTask', backref='firmware', cascade='all, delete-orphan', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'hardware_model': self.hardware_model,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'checksum': self.checksum,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class OtaTask(db.Model):
    """OTA 升级任务"""
    __tablename__ = 'ota_tasks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    firmware_id = db.Column(db.Integer, db.ForeignKey('firmwares.id'), nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    # 目标选择
    target_type = db.Column(db.String(16), default='all', nullable=False)  # all/group/device
    target_ids = db.Column(db.Text, nullable=True)  # JSON 数组，按 target_type 解释
    # 状态
    status = db.Column(db.String(16), default='pending', nullable=False, index=True)  # pending/running/completed/failed/cancelled
    upgrade_mode = db.Column(db.String(16), default='silent', nullable=False)  # silent/force/manual
    scheduled_at = db.Column(db.DateTime, nullable=True)  # 计划执行时间
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    # 统计
    total = db.Column(db.Integer, default=0)
    success = db.Column(db.Integer, default=0)
    failed = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=_now, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    user = db.relationship('User', backref='ota_tasks')
    device_tasks = db.relationship('OtaDeviceTask', backref='task', cascade='all, delete-orphan', lazy='dynamic')

    def to_dict(self):
        import json as _json
        return {
            'id': self.id,
            'firmware_id': self.firmware_id,
            'firmware_name': self.firmware.name if self.firmware else None,
            'firmware_version': self.firmware.version if self.firmware else None,
            'name': self.name,
            'target_type': self.target_type,
            'target_ids': _json.loads(self.target_ids) if self.target_ids else None,
            'status': self.status,
            'upgrade_mode': self.upgrade_mode,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'total': self.total,
            'success': self.success,
            'failed': self.failed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class OtaDeviceTask(db.Model):
    """OTA 单设备升级进度"""
    __tablename__ = 'ota_device_tasks'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('ota_tasks.id', ondelete='CASCADE'), nullable=False, index=True)
    device_id = db.Column(db.Integer, nullable=False, index=True)
    device_name = db.Column(db.String(128), nullable=True)
    status = db.Column(db.String(16), default='pending', nullable=False, index=True)  # pending/downloading/installing/success/failed
    progress = db.Column(db.Integer, default=0)  # 0-100
    error_message = db.Column(db.String(500), nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'device_id': self.device_id,
            'device_name': self.device_name,
            'status': self.status,
            'progress': self.progress,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
        }


class ShadowHistory(db.Model):
    """设备影子变更历史"""
    __tablename__ = 'shadow_history'

    id = db.Column(db.Integer, primary_key=True)
    shadow_id = db.Column(db.Integer, db.ForeignKey('device_shadows.id', ondelete='CASCADE'), nullable=False, index=True)
    device_id = db.Column(db.Integer, nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    
    change_type = db.Column(db.String(16), nullable=False)  # desired_update / reported_update / sync
    old_state = db.Column(db.Text, nullable=True)  # JSON
    new_state = db.Column(db.Text, nullable=True)  # JSON
    version = db.Column(db.Integer, nullable=False)
    
    operator = db.Column(db.String(64), nullable=True)  # user/system/device
    created_at = db.Column(db.DateTime, default=_now, nullable=False, index=True)

    shadow = db.relationship('DeviceShadow', backref=db.backref('history', cascade='all, delete-orphan', lazy='dynamic'))

    def to_dict(self):
        import json as _json
        return {
            'id': self.id,
            'shadow_id': self.shadow_id,
            'device_id': self.device_id,
            'change_type': self.change_type,
            'old_state': _json.loads(self.old_state) if self.old_state else None,
            'new_state': _json.loads(self.new_state) if self.new_state else None,
            'version': self.version,
            'operator': self.operator,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# ========================================================================
# 规则引擎 (Rule Engine)
# ========================================================================

class Rule(db.Model):
    """自动化规则"""
    __tablename__ = 'rules'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    
    # 触发条件 (JSON)
    # 示例: {"device_id": 1, "metric": "temperature", "operator": ">", "value": 50, "duration": 60}
    conditions = db.Column(db.Text, nullable=False)
    
    # 规则状态
    is_enabled = db.Column(db.Boolean, default=True, nullable=False, index=True)
    trigger_count = db.Column(db.Integer, default=0, nullable=False)
    last_triggered_at = db.Column(db.DateTime, nullable=True)
    
    # 优先级 (1-10, 10最高)
    priority = db.Column(db.Integer, default=5, nullable=False)
    
    # 冷却时间 (秒)，防止频繁触发
    cooldown_seconds = db.Column(db.Integer, default=300, nullable=False)
    
    created_at = db.Column(db.DateTime, default=_now, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    user = db.relationship('User', backref='rules')
    actions = db.relationship('RuleAction', backref='rule', cascade='all, delete-orphan', lazy='dynamic')

    def to_dict(self):
        import json as _json
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'conditions': _json.loads(self.conditions) if self.conditions else {},
            'is_enabled': self.is_enabled,
            'trigger_count': self.trigger_count,
            'last_triggered_at': self.last_triggered_at.isoformat() if self.last_triggered_at else None,
            'priority': self.priority,
            'cooldown_seconds': self.cooldown_seconds,
            'actions': [a.to_dict() for a in self.actions],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class RuleAction(db.Model):
    """规则动作"""
    __tablename__ = 'rule_actions'

    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('rules.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # 动作类型: alarm / command / notification / webhook
    action_type = db.Column(db.String(32), nullable=False)
    
    # 动作配置 (JSON)
    # alarm: {"severity": "warning", "message": "温度过高"}
    # command: {"device_id": 1, "command": "reboot"}
    # notification: {"channel": "email", "recipients": ["admin@example.com"]}
    # webhook: {"url": "https://...", "method": "POST", "headers": {...}}
    config = db.Column(db.Text, nullable=False)
    
    # 执行顺序
    order = db.Column(db.Integer, default=0, nullable=False)
    
    created_at = db.Column(db.DateTime, default=_now, nullable=False)

    def to_dict(self):
        import json as _json
        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'action_type': self.action_type,
            'config': _json.loads(self.config) if self.config else {},
            'order': self.order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class RuleExecutionLog(db.Model):
    """规则执行日志"""
    __tablename__ = 'rule_execution_logs'

    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('rules.id', ondelete='CASCADE'), nullable=False, index=True)
    device_id = db.Column(db.Integer, nullable=True, index=True)
    
    # 触发时的数据快照 (JSON)
    trigger_data = db.Column(db.Text, nullable=True)
    
    # 执行结果
    status = db.Column(db.String(16), nullable=False)  # success / failed / skipped
    error_message = db.Column(db.String(500), nullable=True)
    
    # 执行的动作结果 (JSON)
    action_results = db.Column(db.Text, nullable=True)
    
    executed_at = db.Column(db.DateTime, default=_now, nullable=False, index=True)

    rule = db.relationship('Rule', backref=db.backref('execution_logs', cascade='all, delete-orphan', lazy='dynamic'))

    def to_dict(self):
        import json as _json
        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'rule_name': self.rule.name if self.rule else None,
            'device_id': self.device_id,
            'trigger_data': _json.loads(self.trigger_data) if self.trigger_data else None,
            'status': self.status,
            'error_message': self.error_message,
            'action_results': _json.loads(self.action_results) if self.action_results else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
        }


# ========================================================================
# 自定义大屏 (Custom Dashboard)
# ========================================================================

class DashboardLayout(db.Model):
    """自定义大屏布局"""
    __tablename__ = 'dashboard_layouts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    
    # 布局配置 (JSON) - 包含所有 widget 的位置和大小
    layout_config = db.Column(db.Text, nullable=True)
    
    # 是否为默认大屏
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    
    # 访问权限: private / shared / public
    visibility = db.Column(db.String(16), default='private', nullable=False)
    
    # 主题配置 (JSON)
    theme_config = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=_now, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    user = db.relationship('User', backref='dashboard_layouts')
    widgets = db.relationship('DashboardWidget', backref='layout', cascade='all, delete-orphan', lazy='dynamic')

    def to_dict(self):
        import json as _json
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'layout_config': _json.loads(self.layout_config) if self.layout_config else [],
            'is_default': self.is_default,
            'visibility': self.visibility,
            'theme_config': _json.loads(self.theme_config) if self.theme_config else {},
            'widgets': [w.to_dict() for w in self.widgets],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class DashboardWidget(db.Model):
    """大屏组件"""
    __tablename__ = 'dashboard_widgets'

    id = db.Column(db.Integer, primary_key=True)
    layout_id = db.Column(db.Integer, db.ForeignKey('dashboard_layouts.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # 组件类型: chart / gauge / stat / map / table / text / image
    widget_type = db.Column(db.String(32), nullable=False)
    
    # 组件标题
    title = db.Column(db.String(128), nullable=True)
    
    # 位置和大小 (grid 系统)
    x = db.Column(db.Integer, default=0, nullable=False)
    y = db.Column(db.Integer, default=0, nullable=False)
    w = db.Column(db.Integer, default=4, nullable=False)  # 宽度 (grid units)
    h = db.Column(db.Integer, default=3, nullable=False)  # 高度 (grid units)
    
    # 数据源配置 (JSON)
    # 示例: {"device_id": 1, "metric": "temperature", "chart_type": "line"}
    data_config = db.Column(db.Text, nullable=True)
    
    # 样式配置 (JSON)
    style_config = db.Column(db.Text, nullable=True)
    
    # 刷新间隔 (秒)
    refresh_interval = db.Column(db.Integer, default=30, nullable=False)
    
    # 排序
    order = db.Column(db.Integer, default=0, nullable=False)
    
    created_at = db.Column(db.DateTime, default=_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    def to_dict(self):
        import json as _json
        return {
            'id': self.id,
            'layout_id': self.layout_id,
            'widget_type': self.widget_type,
            'title': self.title,
            'x': self.x,
            'y': self.y,
            'w': self.w,
            'h': self.h,
            'data_config': _json.loads(self.data_config) if self.data_config else {},
            'style_config': _json.loads(self.style_config) if self.style_config else {},
            'refresh_interval': self.refresh_interval,
            'order': self.order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# ========================================================================
# 协议消息日志 (Protocol Message)
# ========================================================================

class ProtocolMessage(db.Model):
    """协议消息日志"""
    __tablename__ = 'protocol_messages'

    id = db.Column(db.Integer, primary_key=True)
    adapter_id = db.Column(db.Integer, db.ForeignKey('protocol_adapters.id', ondelete='CASCADE'), nullable=False, index=True)
    device_id = db.Column(db.Integer, nullable=True, index=True)
    
    # 消息方向: inbound (设备→平台) / outbound (平台→设备)
    direction = db.Column(db.String(16), nullable=False)
    
    # 原始消息 (JSON)
    raw_payload = db.Column(db.Text, nullable=True)
    
    # 解析后的数据 (JSON)
    parsed_data = db.Column(db.Text, nullable=True)
    
    # 消息状态: success / failed / timeout
    status = db.Column(db.String(16), default='success', nullable=False, index=True)
    error_message = db.Column(db.String(500), nullable=True)
    
    # 元数据
    topic = db.Column(db.String(256), nullable=True)  # MQTT topic / CoAP URI
    qos = db.Column(db.Integer, nullable=True)  # MQTT QoS
    
    created_at = db.Column(db.DateTime, default=_now, nullable=False, index=True)

    def to_dict(self):
        import json as _json
        return {
            'id': self.id,
            'adapter_id': self.adapter_id,
            'device_id': self.device_id,
            'direction': self.direction,
            'raw_payload': _json.loads(self.raw_payload) if self.raw_payload else None,
            'parsed_data': _json.loads(self.parsed_data) if self.parsed_data else None,
            'status': self.status,
            'error_message': self.error_message,
            'topic': self.topic,
            'qos': self.qos,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
