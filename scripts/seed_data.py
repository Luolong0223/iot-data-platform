"""
IoT平台测试数据生成脚本
生成设备、数据点、告警等测试数据
"""
import sys
import os
import random
from datetime import datetime, timedelta, timezone

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 强制使用SQLite (使用现有的instance/database.db)
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'instance/database.db'
)

from flask import Flask
from config import config
from models.database import (
    db, User, Project, Device, SlaveChannel, DataPoint, AlarmRecord
)


def create_app_for_seed():
    app = Flask(__name__)
    app.config.from_object(config['development'])
    db.init_app(app)
    with app.app_context():
        db.create_all()
    return app


def utcnow():
    return datetime.now(timezone.utc)


def ensure_user_and_project():
    """确保存在管理员用户和默认项目"""
    user = User.query.filter_by(username='admin').first()
    if not user:
        user = User(
            username='admin',
            email='admin@iot.local',
            is_admin=True,
            is_active=True,
            storage_enabled=True
        )
        user.set_password('admin123')
        db.session.add(user)
        db.session.commit()
        print(f"  ✅ 创建用户: admin / admin123")

    project = Project.query.filter_by(user_id=user.id).first()
    if not project:
        project = Project(
            user_id=user.id,
            name='默认项目',
            description='测试用默认项目',
            location='中国',
            color='#3b82f6',
            sort_order=0
        )
        db.session.add(project)
        db.session.commit()
        print(f"  ✅ 创建项目: 默认项目")

    return user, project


def generate_devices(user, project, count=10):
    """生成测试设备"""
    device_specs = [
        ('temperature', '温度传感器', '北京', 39.9042, 116.4074),
        ('humidity', '湿度传感器', '上海', 31.2304, 121.4737),
        ('pressure', '压力传感器', '广州', 23.1291, 113.2644),
        ('flow', '流量计', '深圳', 22.5431, 114.0579),
        ('electric', '电表', '杭州', 30.2741, 120.1551),
        ('temperature', '温度传感器', '成都', 30.5728, 104.0668),
        ('humidity', '湿度传感器', '武汉', 30.5928, 114.3055),
        ('pressure', '压力传感器', '西安', 34.3416, 108.9398),
        ('flow', '流量计', '南京', 32.0603, 118.7969),
        ('electric', '电表', '重庆', 29.4316, 106.9123),
    ]

    devices = []
    now = utcnow()
    for i, (dtype, name_prefix, location, lat, lng) in enumerate(device_specs[:count]):
        is_online = random.random() > 0.3
        device = Device(
            user_id=user.id,
            project_id=project.id,
            name=f'{name_prefix}-{i+1:02d}',
            device_type=dtype,
            device_key=f'KEY-{1000+i}',
            latitude=lat + random.uniform(-0.05, 0.05),
            longitude=lng + random.uniform(-0.05, 0.05),
            location_name=location,
            ip_address=f'192.168.1.{100+i}',
            firmware_version='1.0.0',
            voltage_mv=random.randint(3500, 4200),
            is_online=is_online,
            last_seen_at=now - timedelta(minutes=random.randint(0, 60)) if is_online else None,
            storage_enabled=True,
            maintenance_interval=30,
            last_maintenance_at=now - timedelta(days=random.randint(0, 30))
        )
        devices.append(device)
        db.session.add(device)
    db.session.commit()
    return devices


def generate_channels_and_data(devices, points_per_device=24):
    """为每个设备创建通道并生成数据点"""
    all_data_points = []
    now = utcnow()

    for device in devices:
        # 每个设备创建一个通道
        channel = SlaveChannel(
            device_id=device.id,
            name='sensor_data',
            online=device.is_online,
            last_data_at=now
        )
        db.session.add(channel)
        db.session.flush()  # 获取channel.id

        # 生成数据点（24小时内每小时一个点）
        for i in range(points_per_device):
            dp = DataPoint(
                channel_id=channel.id,
                name='value',
                value=round(random.uniform(20, 90), 2),
                timestamp=now - timedelta(hours=i, minutes=random.randint(0, 59))
            )
            all_data_points.append(dp)
            db.session.add(dp)

    db.session.commit()
    return all_data_points


def generate_alarms(user, devices, count=8):
    """生成测试告警"""
    severities = ['critical', 'warning', 'info']
    messages = [
        '温度超过阈值',
        '压力异常',
        '流量过低',
        '电压波动',
        '通信中断',
        '数据异常',
        '电池电量低',
        '传感器故障'
    ]

    alarms = []
    now = utcnow()
    for i in range(count):
        device = random.choice(devices)
        severity = random.choice(severities)
        alarm = AlarmRecord(
            user_id=user.id,
            device_name=device.name,
            channel_name='sensor_data',
            point_name='value',
            value=round(random.uniform(0, 100), 2),
            threshold=80.0,
            condition='>',
            severity=severity,
            message=f"{device.name}: {random.choice(messages)}",
            is_read=random.random() > 0.5,
            is_handled=random.random() > 0.7,
            created_at=now - timedelta(hours=random.randint(0, 48))
        )
        alarms.append(alarm)
        db.session.add(alarm)
    db.session.commit()
    return alarms


def main():
    app = create_app_for_seed()
    with app.app_context():
        print("=" * 50)
        print("IoT平台测试数据生成")
        print("=" * 50)

        # 确保基础数据
        print("\n[0/3] 准备用户和项目...")
        user, project = ensure_user_and_project()

        # 创建设备
        print("\n[1/3] 生成设备数据...")
        existing = Device.query.count()
        if existing < 5:
            devices = generate_devices(user, project, count=10)
            print(f"  ✅ 新增 {len(devices)} 台设备")
        else:
            print(f"  ⏭️  已有 {existing} 台设备，复用")
            devices = Device.query.all()

        # 生成数据点
        print("\n[2/3] 生成数据点...")
        existing_dp = DataPoint.query.count()
        if existing_dp < 100:
            data_points = generate_channels_and_data(devices, points_per_device=24)
            print(f"  ✅ 新增 {len(data_points)} 个数据点")
        else:
            print(f"  ⏭️  已有 {existing_dp} 个数据点，跳过")

        # 生成告警
        print("\n[3/3] 生成告警...")
        existing_alarm = AlarmRecord.query.count()
        if existing_alarm < 5:
            alarms = generate_alarms(user, devices, count=8)
            print(f"  ✅ 新增 {len(alarms)} 条告警")
        else:
            print(f"  ⏭️  已有 {existing_alarm} 条告警，跳过")

        # 统计
        print("\n" + "=" * 50)
        print("数据统计:")
        print(f"  用户: {User.query.count()}")
        print(f"  项目: {Project.query.count()}")
        print(f"  设备总数: {Device.query.count()}")
        print(f"  在线设备: {Device.query.filter_by(is_online=True).count()}")
        print(f"  离线设备: {Device.query.filter_by(is_online=False).count()}")
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        print(f"  数据点总数: {DataPoint.query.count()}")
        print(f"  今日数据点: {DataPoint.query.filter(DataPoint.timestamp >= today_start).count()}")
        print(f"  告警总数: {AlarmRecord.query.count()}")
        print(f"  未处理告警: {AlarmRecord.query.filter_by(is_handled=False).count()}")
        print(f"  通道数: {SlaveChannel.query.count()}")
        print("=" * 50)


if __name__ == '__main__':
    main()
