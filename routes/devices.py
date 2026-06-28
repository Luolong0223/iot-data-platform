"""
设备管理路由 - 设备 CRUD + 分类树 CRUD
"""
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from sqlalchemy import desc
from models.database import db, Device, Channel, DataPoint, DataHistory, DeviceCategory

devices_bp = Blueprint('devices', __name__, url_prefix='/api/devices')


# ================= 页面 =================
@devices_bp.route('/')
@login_required
def page():
    return render_template('devices.html')


# ================= API: 设备列表 =================
@devices_bp.route('/devices', methods=['GET'])
@login_required
def list_devices():
    try:
        category_id = request.args.get('category_id', type=int)
        q = Device.query.filter_by(user_id=current_user.id)
        if category_id is not None:
            # 包含该分类及其所有子分类的设备
            cat_ids = collect_category_ids(category_id)
            q = q.filter(Device.category_id.in_(cat_ids))
        devices = q.order_by(desc(Device.last_seen)).all()
        return jsonify({'success': True, 'data': [d.to_dict() for d in devices]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@devices_bp.route('/devices/<int:device_id>', methods=['GET'])
@login_required
def get_device(device_id):
    try:
        d = Device.query.get(device_id)
        if not d or d.user_id != current_user.id:
            return jsonify({'success': False, 'error': '设备不存在'}), 404
        return jsonify({'success': True, 'data': d.to_dict(with_channels=True)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@devices_bp.route('/devices/<int:device_id>', methods=['PUT'])
@login_required
def update_device(device_id):
    try:
        d = Device.query.get(device_id)
        if not d or d.user_id != current_user.id:
            return jsonify({'success': False, 'error': '设备不存在'}), 404
        body = request.get_json() or {}
        if 'custom_name' in body:
            d.custom_name = body['custom_name'] or None
        if 'description' in body:
            d.description = body['description'] or None
        if 'category_id' in body:
            new_cat_id = body['category_id']
            if new_cat_id is not None:
                # 验证分类存在且属于当前用户
                cat = DeviceCategory.query.get(new_cat_id)
                if not cat or cat.user_id != current_user.id:
                    return jsonify({'success': False, 'error': '分类不存在'}), 400
            d.category_id = new_cat_id
        db.session.commit()
        return jsonify({'success': True, 'data': d.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@devices_bp.route('/devices/<int:device_id>', methods=['DELETE'])
@login_required
def delete_device(device_id):
    try:
        d = Device.query.get(device_id)
        if not d or d.user_id != current_user.id:
            return jsonify({'success': False, 'error': '设备不存在'}), 404
        # 级联删除: channels, data_points, data_history 通过模型 cascade
        db.session.delete(d)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ================= API: 分类树 =================
@devices_bp.route('/categories', methods=['GET'])
@login_required
def list_categories():
    try:
        cats = DeviceCategory.query.filter_by(user_id=current_user.id).order_by(DeviceCategory.sort_order).all()
        # 构造树
        tree = build_category_tree(cats, parent_id=None)
        # 计算每个分类的设备数
        count_map = {}
        for d in Device.query.filter_by(user_id=current_user.id).all():
            cid = d.category_id
            if cid is not None:
                # 累加到该分类
                count_map[cid] = count_map.get(cid, 0) + 1
        def attach_count(nodes):
            for n in nodes:
                n['device_count'] = count_map.get(n['id'], 0)
                attach_count(n.get('children', []))
        attach_count(tree)
        return jsonify({'success': True, 'data': tree})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@devices_bp.route('/categories', methods=['POST'])
@login_required
def create_category():
    try:
        body = request.get_json() or {}
        name = (body.get('name') or '').strip()
        if not name:
            return jsonify({'success': False, 'error': '分类名不能为空'}), 400
        parent_id = body.get('parent_id')
        if parent_id is not None:
            parent = DeviceCategory.query.get(parent_id)
            if not parent or parent.user_id != current_user.id:
                return jsonify({'success': False, 'error': '父分类不存在'}), 400
        cat = DeviceCategory(
            name=name,
            parent_id=parent_id,
            user_id=current_user.id,
            sort_order=body.get('sort_order', 0),
            created_at=datetime.utcnow()
        )
        db.session.add(cat)
        db.session.commit()
        return jsonify({'success': True, 'data': cat.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@devices_bp.route('/categories/<int:cat_id>', methods=['PUT'])
@login_required
def update_category(cat_id):
    try:
        cat = DeviceCategory.query.get(cat_id)
        if not cat or cat.user_id != current_user.id:
            return jsonify({'success': False, 'error': '分类不存在'}), 404
        body = request.get_json() or {}
        if 'name' in body:
            name = (body['name'] or '').strip()
            if not name:
                return jsonify({'success': False, 'error': '分类名不能为空'}), 400
            cat.name = name
        if 'sort_order' in body:
            cat.sort_order = body['sort_order']
        db.session.commit()
        return jsonify({'success': True, 'data': cat.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@devices_bp.route('/categories/<int:cat_id>', methods=['DELETE'])
@login_required
def delete_category(cat_id):
    try:
        cat = DeviceCategory.query.get(cat_id)
        if not cat or cat.user_id != current_user.id:
            return jsonify({'success': False, 'error': '分类不存在'}), 404
        # 把子分类上移一级,把设备变为未分类
        for child in list(cat.children):
            child.parent_id = cat.parent_id
        # 设备解除分类
        Device.query.filter_by(category_id=cat_id, user_id=current_user.id)\
            .update({Device.category_id: None}, synchronize_session=False)
        db.session.delete(cat)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ================= 辅助函数 =================
def build_category_tree(all_cats, parent_id=None):
    """根据扁平的分类列表构造树"""
    result = []
    for c in all_cats:
        if c.parent_id == parent_id:
            d = c.to_dict(with_children=False)
            d['children'] = build_category_tree(all_cats, c.id)
            result.append(d)
    return result


def collect_category_ids(root_id):
    """收集分类及其所有子分类的 ID（单次查询）"""
    result = [root_id]
    # 一次性查询所有相关分类
    all_cats = DeviceCategory.query.filter(
        DeviceCategory.parent_id.isnot(None)
    ).all()
    # 构建 parent_id -> children 的映射
    children_map = {}
    for c in all_cats:
        if c.parent_id not in children_map:
            children_map[c.parent_id] = []
        children_map[c.parent_id].append(c.id)
    
    # BFS 遍历子分类
    queue = [root_id]
    while queue:
        pid = queue.pop(0)
        if pid in children_map:
            for child_id in children_map[pid]:
                result.append(child_id)
                queue.append(child_id)
    return result
