"""
IoT平台测试数据生成脚本
生成设备、数据点等测试数据
"""
import sys
import os
import random
from datetime import datetime, timedelta, timezone

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 强制使用SQLite
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'instance/database.db'
)

from flask import Flask
from config import config
from models.database import (
    db, User, Device, Channel, DataPoint, DataHistory
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


def ensure_user():
    """确保存在管理员用户"""
    user = User.query.filter_by(username='admin').first()
    if not user:
        user = User(
            username='admin',
            email='admin@iot.local',
            is_admin=True,
            is_active=True
        )
        user.set_password('admin123')
        db.session.add(user)
        db.session.commit()
        print("  Created user: admin / admin123")
    return user


def generate_devices(user, count=10):
    """生成测试设备"""
    device_specs = [
        ('temperature', '温度传感器', '北京'),
        ('humidity', '湿度传感器', '上海'),
        ('pressure', '压力传感器', '广州'),
        ('flow', '流量计', '深圳'),
        ('electric', '电表', '杭州'),
        ('temperature', '温度传感器', '成都'),
        ('humidity', '湿度传感器', '武汉'),
        ('pressure', '压力传感器', '西安'),
        ('flow', '流量计', '南京'),
        ('electric', '电表', '重庆'),
    ]

    devices = []
    now = utcnow()
    for i, (dtype, name_prefix, location) in enumerate(device_specs[:count]):
        is_online = random.random() > 0.3
        device = Device(
            user_id=user.id,
            name=f'{name_prefix}-{i+1:02d}',
            voltage_mv=random.randint(3500, 4200),
            is_online=is_online,
            last_seen=now - timedelta(minutes=random.randint(0, 60)) if is_online else now,
            first_seen=now - timedelta(days=random.randint(1, 30)),
            total_packets=random.randint(100, 10000)
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
        channel = Channel(
            device_id=device.id,
            name='sensor_data',
            is_online=device.is_online,
            last_seen=now,
            first_seen=device.first_seen
        )
        db.session.add(channel)
        db.session.flush()

        # 生成数据点（24小时内每小时一个点）
        for i in range(points_per_device):
            value = round(random.uniform(20, 90), 2)
            dp = DataPoint(
                channel_id=channel.id,
                name='value',
                value=value,
                last_value=value - random.uniform(-5, 5),
                last_updated=now - timedelta(hours=i),
                update_count=1
            )
            all_data_points.append(dp)
            db.session.add(dp)
            db.session.flush()

            # 写入历史
            hist = DataHistory(
                data_point_id=dp.id,
                device_id=device.id,
                channel_id=channel.id,
                value=value,
                timestamp=now - timedelta(hours=i)
            )
            db.session.add(hist)

    db.session.commit()
    return all_data_points


def main():
    app = create_app_for_seed()
    with app.app_context():
        print("=" * 50)
        print("IoT平台测试数据生成")
        print("=" * 50)

        # 确保基础数据
        print("\n[1/2] 准备用户...")
        user = ensure_user()

        # 创建设备
        print("\n[2/2] 生成设备和数据点...")
        existing = Device.query.count()
        if existing < 5:
            devices = generate_devices(user, count=10)
            print(f"  Created {len(devices)} devices")
        else:
            print(f"  Already have {existing} devices, skipping")
            devices = Device.query.all()

        # 生成数据点
        existing_dp = DataPoint.query.count()
        if existing_dp < 100:
            data_points = generate_channels_and_data(devices, points_per_device=24)
            print(f"  Created {len(data_points)} data points")
        else:
            print(f"  Already have {existing_dp} data points, skipping")

        # 统计
        print("\n" + "=" * 50)
        print("Statistics:")
        print(f"  Users: {User.query.count()}")
        print(f"  Devices: {Device.query.count()}")
        print(f"  Online devices: {Device.query.filter_by(is_online=True).count()}")
        print(f"  Offline devices: {Device.query.filter_by(is_online=False).count()}")
        print(f"  Channels: {Channel.query.count()}")
        print(f"  Data points: {DataPoint.query.count()}")
        print(f"  Data history: {DataHistory.query.count()}")
        print("=" * 50)


if __name__ == '__main__':
    main()
