"""
OTA 固件升级服务
- 固件包上传/管理
- 升级任务创建（按全量/分组/单设备）
- 升级进度跟踪
"""
import os
import json
import hashlib
import threading
from datetime import datetime
from typing import List, Optional

from flask import current_app
from werkzeug.utils import secure_filename

from models.database import db, Firmware, OtaTask, OtaDeviceTask, Device, DeviceGroup


# 固件文件存放目录
FIRMWARE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'firmwares')
os.makedirs(FIRMWARE_DIR, exist_ok=True)


def _save_firmware_file(file_storage, user_id: int) -> tuple:
    """保存固件文件到本地，返回 (filename, file_path, file_size, checksum)"""
    if not file_storage or not file_storage.filename:
        raise ValueError('empty file')
    safe = secure_filename(file_storage.filename)
    # 用户子目录
    user_dir = os.path.join(FIRMWARE_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    file_path = os.path.join(user_dir, safe)
    # 同名追加时间戳
    if os.path.exists(file_path):
        name, ext = os.path.splitext(safe)
        safe = f'{name}_{int(datetime.utcnow().timestamp())}{ext}'
        file_path = os.path.join(user_dir, safe)
    file_storage.save(file_path)
    file_size = os.path.getsize(file_path)
    # 计算 md5
    h = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    checksum = h.hexdigest()
    rel_path = os.path.relpath(file_path, os.path.dirname(FIRMWARE_DIR))
    return safe, rel_path, file_size, checksum


def create_firmware(user_id: int, name: str, version: str,
                    hardware_model: Optional[str], file_storage,
                    description: str = '') -> Firmware:
    filename, rel_path, size, checksum = _save_firmware_file(file_storage, user_id)
    fw = Firmware(
        user_id=user_id, name=name, version=version,
        hardware_model=hardware_model, file_path=rel_path,
        file_size=size, checksum=checksum, description=description
    )
    db.session.add(fw)
    db.session.commit()
    return fw


def create_ota_task(user_id: int, firmware_id: int, name: str,
                    target_type: str, target_ids: Optional[List[int]],
                    upgrade_mode: str = 'silent',
                    scheduled_at: Optional[datetime] = None) -> OtaTask:
    """创建 OTA 任务，按 target_type 解析目标设备并展开为 OtaDeviceTask"""
    if target_type not in ('all', 'group', 'device'):
        raise ValueError(f'invalid target_type: {target_type}')

    # 解析目标设备 ID 列表
    device_ids: List[int] = []
    q = Device.query.filter_by(user_id=user_id)
    if target_type == 'all':
        device_ids = [d.id for d in q.all()]
    elif target_type == 'group':
        # target_ids 是分组 id 列表
        target_ids = target_ids or []
        # 简单实现：取所有 group 下的设备并去重
        all_devs = set()
        for gid in target_ids:
            g = DeviceGroup.query.filter_by(id=gid, user_id=user_id).first()
            if g and g.devices:
                for d in g.devices:
                    all_devs.add(d.id)
        device_ids = list(all_devs)
    elif target_type == 'device':
        target_ids = target_ids or []
        device_ids = [int(x) for x in target_ids if q.filter_by(id=int(x)).first()]

    task = OtaTask(
        user_id=user_id, firmware_id=firmware_id, name=name,
        target_type=target_type, target_ids=json.dumps(target_ids) if target_ids else None,
        upgrade_mode=upgrade_mode, scheduled_at=scheduled_at,
        status='pending', total=len(device_ids)
    )
    db.session.add(task)
    db.session.flush()

    # 展开为单设备任务
    for did in device_ids:
        dev = q.filter_by(id=did).first()
        if not dev:
            continue
        dt = OtaDeviceTask(
            task_id=task.id, device_id=did, device_name=dev.name, status='pending', progress=0
        )
        db.session.add(dt)

    db.session.commit()
    return task


def start_task(task_id: int) -> int:
    """将任务状态切到 running 并返回设备子任务数"""
    task = OtaTask.query.get(task_id)
    if not task or task.status not in ('pending',):
        return 0
    task.status = 'running'
    task.started_at = datetime.utcnow()
    db.session.commit()
    return task.device_tasks.count()


def report_device_progress(task_id: int, device_id: int,
                           status: str, progress: int = 0,
                           error: str = '') -> bool:
    """设备回报升级进度（设备端调用）"""
    dt = OtaDeviceTask.query.filter_by(task_id=task_id, device_id=device_id).first()
    if not dt:
        return False
    dt.status = status
    dt.progress = max(0, min(100, int(progress)))
    if error:
        dt.error_message = error[:500]
    if status in ('success', 'failed') and not dt.finished_at:
        dt.finished_at = datetime.utcnow()
    db.session.commit()

    # 汇总到主任务
    task = OtaTask.query.get(task_id)
    if task:
        succ = task.device_tasks.filter_by(status='success').count()
        fail = task.device_tasks.filter_by(status='failed').count()
        task.success = succ
        task.failed = fail
        if (succ + fail) >= task.total:
            task.status = 'completed' if fail == 0 else 'partial'
            task.finished_at = datetime.utcnow()
        db.session.commit()
    return True


def cancel_task(task_id: int) -> bool:
    task = OtaTask.query.get(task_id)
    if not task or task.status in ('completed', 'cancelled'):
        return False
    task.status = 'cancelled'
    task.finished_at = datetime.utcnow()
    for dt in task.device_tasks.filter(OtaDeviceTask.status.in_(['pending', 'downloading', 'installing'])).all():
        dt.status = 'cancelled'
    db.session.commit()
    return True
