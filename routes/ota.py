"""
OTA 固件升级 API
"""
import os
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file, current_app
from flask_login import login_required, current_user

from models.database import db, Firmware, OtaTask, OtaDeviceTask
from services.rbac import require_permission
import services.ota as ota_svc

# 固件根目录
FIRMWARE_BASE = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'instance'))

ota_bp = Blueprint('ota', __name__, url_prefix='/api/ota')


# ============= 固件包 =============

@ota_bp.route('/firmwares', methods=['GET'])
@login_required
@require_permission('device.read')
def list_firmwares():
    fws = Firmware.query.filter_by(user_id=current_user.id).order_by(Firmware.id.desc()).all()
    return jsonify({'success': True, 'data': [f.to_dict() for f in fws]})


@ota_bp.route('/firmwares', methods=['POST'])
@login_required
@require_permission('device.write')
def upload_firmware():
    name = (request.form.get('name') or '').strip()
    version = (request.form.get('version') or '').strip()
    hardware_model = (request.form.get('hardware_model') or '').strip() or None
    description = (request.form.get('description') or '').strip()
    file = request.files.get('file')
    if not name or not version or not file:
        return jsonify({'success': False, 'msg': 'name/version/file 必填'}), 400
    try:
        fw = ota_svc.create_firmware(
            user_id=current_user.id, name=name, version=version,
            hardware_model=hardware_model, file_storage=file, description=description
        )
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)}), 400
    return jsonify({'success': True, 'data': fw.to_dict()}), 201


@ota_bp.route('/firmwares/<int:fw_id>', methods=['DELETE'])
@login_required
@require_permission('device.write')
def delete_firmware(fw_id):
    fw = Firmware.query.filter_by(id=fw_id, user_id=current_user.id).first()
    if not fw:
        return jsonify({'success': False, 'msg': '固件不存在'}), 404
    # 关联任务阻止删除
    if fw.tasks.count() > 0:
        return jsonify({'success': False, 'msg': f'固件已被 {fw.tasks.count()} 个任务使用，不能删除'}), 400
    # 删除文件
    try:
        full_path = os.path.normpath(os.path.join(FIRMWARE_BASE, fw.file_path))
        if os.path.isfile(full_path):
            os.remove(full_path)
    except Exception:
        pass
    db.session.delete(fw)
    db.session.commit()
    return jsonify({'success': True})


@ota_bp.route('/firmwares/<int:fw_id>/download', methods=['GET'])
@login_required
@require_permission('device.read')
def download_firmware(fw_id):
    fw = Firmware.query.filter_by(id=fw_id, user_id=current_user.id).first()
    if not fw:
        return jsonify({'success': False, 'msg': '固件不存在'}), 404
    full_path = os.path.normpath(os.path.join(FIRMWARE_BASE, fw.file_path))
    if not os.path.isfile(full_path):
        return jsonify({'success': False, 'msg': '固件文件丢失'}), 404
    return send_file(full_path, as_attachment=True, download_name=f'{fw.name}_{fw.version}.bin')


# ============= 升级任务 =============

@ota_bp.route('/tasks', methods=['GET'])
@login_required
@require_permission('device.read')
def list_tasks():
    qs = OtaTask.query
    if not current_user.is_admin:
        qs = qs.filter_by(user_id=current_user.id)
    tasks = qs.order_by(OtaTask.id.desc()).all()
    return jsonify({'success': True, 'data': [t.to_dict() for t in tasks]})


@ota_bp.route('/tasks', methods=['POST'])
@login_required
@require_permission('device.write')
def create_task():
    data = request.get_json() or {}
    firmware_id = data.get('firmware_id')
    name = (data.get('name') or '').strip()
    target_type = data.get('target_type', 'all')
    target_ids = data.get('target_ids') or []
    upgrade_mode = data.get('upgrade_mode', 'silent')
    scheduled_at_raw = data.get('scheduled_at')
    if not firmware_id or not name:
        return jsonify({'success': False, 'msg': 'firmware_id 和 name 必填'}), 400
    fw = Firmware.query.filter_by(id=firmware_id, user_id=current_user.id).first()
    if not fw:
        return jsonify({'success': False, 'msg': '固件不存在'}), 404
    scheduled_at = None
    if scheduled_at_raw:
        try:
            scheduled_at = datetime.fromisoformat(scheduled_at_raw)
        except ValueError:
            return jsonify({'success': False, 'msg': 'scheduled_at 格式错误（ISO8601）'}), 400
    try:
        task = ota_svc.create_ota_task(
            user_id=current_user.id, firmware_id=firmware_id, name=name,
            target_type=target_type, target_ids=target_ids,
            upgrade_mode=upgrade_mode, scheduled_at=scheduled_at
        )
    except Exception as e:
        return jsonify({'success': False, 'msg': str(e)}), 400
    return jsonify({'success': True, 'data': task.to_dict()}), 201


@ota_bp.route('/tasks/<int:task_id>/start', methods=['POST'])
@login_required
@require_permission('device.write')
def start_task(task_id):
    task = OtaTask.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        return jsonify({'success': False, 'msg': '任务不存在'}), 404
    n = ota_svc.start_task(task_id)
    return jsonify({'success': True, 'device_count': n})


@ota_bp.route('/tasks/<int:task_id>/cancel', methods=['POST'])
@login_required
@require_permission('device.write')
def cancel_task(task_id):
    task = OtaTask.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        return jsonify({'success': False, 'msg': '任务不存在'}), 404
    ok = ota_svc.cancel_task(task_id)
    return jsonify({'success': ok})


@ota_bp.route('/tasks/<int:task_id>', methods=['GET'])
@login_required
@require_permission('device.read')
def task_detail(task_id):
    task = OtaTask.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        return jsonify({'success': False, 'msg': '任务不存在'}), 404
    data = task.to_dict()
    data['devices'] = [d.to_dict() for d in task.device_tasks.order_by(OtaDeviceTask.id).all()]
    return jsonify({'success': True, 'data': data})


# ============= 设备端进度回报 =============

@ota_bp.route('/tasks/<int:task_id>/devices/<int:device_id>/progress', methods=['POST'])
@login_required
@require_permission('device.write')
def report_progress(task_id, device_id):
    data = request.get_json() or {}
    ok = ota_svc.report_device_progress(
        task_id=task_id, device_id=device_id,
        status=data.get('status', 'pending'),
        progress=int(data.get('progress', 0)),
        error=data.get('error', '')
    )
    return jsonify({'success': ok})


# ============= 设备轮询：获取待执行任务 =============

@ota_bp.route('/devices/<int:device_id>/pending', methods=['GET'])
@login_required
@require_permission('device.read')
def get_pending_for_device(device_id):
    """设备端调用：取自己待执行的升级任务"""
    q = OtaDeviceTask.query.join(OtaTask).filter(
        OtaDeviceTask.device_id == device_id,
        OtaTask.status == 'running',
        OtaDeviceTask.status.in_(['pending', 'downloading', 'installing'])
    )
    items = []
    for dt in q.all():
        fw = dt.task.firmware
        items.append({
            'task_id': dt.task_id,
            'device_task_id': dt.id,
            'firmware': {
                'id': fw.id, 'name': fw.name, 'version': fw.version,
                'file_path': fw.file_path, 'file_size': fw.file_size,
                'checksum': fw.checksum
            },
            'upgrade_mode': dt.task.upgrade_mode,
            'status': dt.status,
            'progress': dt.progress,
        })
    return jsonify({'success': True, 'data': items})
