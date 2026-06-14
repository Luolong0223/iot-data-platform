"""
RBAC 角色权限管理 API
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models.database import db, Role, Permission, RolePermission, UserRole, User
from services.rbac import RBACService, require_permission, DEFAULT_PERMISSIONS

rbac_bp = Blueprint('rbac', __name__, url_prefix='/api/rbac')


@rbac_bp.route('/permissions', methods=['GET'])
@login_required
def list_permissions():
    """获取所有权限定义"""
    perms = Permission.query.order_by(Permission.resource, Permission.id).all()
    return jsonify({'success': True, 'data': [p.to_dict() for p in perms]})


@rbac_bp.route('/roles', methods=['GET'])
@login_required
def list_roles():
    """获取所有角色（系统角色 + 当前用户自建角色）"""
    user_id = current_user.id
    if current_user.is_admin:
        roles = Role.query.all()
    else:
        roles = Role.query.filter(
            (Role.user_id == user_id) | (Role.is_system == True)
        ).all()
    return jsonify({'success': True, 'data': [r.to_dict() for r in roles]})


@rbac_bp.route('/roles', methods=['POST'])
@login_required
@require_permission('role.write')
def create_role():
    """创建角色"""
    data = request.get_json() or {}
    code = data.get('code', '').strip()
    if not code or not data.get('name', '').strip():
        return jsonify({'success': False, 'msg': '名称与代码必填'}), 400
    if code in ('admin', 'operator', 'viewer'):
        return jsonify({'success': False, 'msg': f'系统保留角色名: {code}'}), 400

    # 系统角色（code 以 sys_ 开头）user_id=None；普通角色挂在当前用户下
    is_system = code.startswith('sys_') and current_user.is_admin
    role_user_id = None if is_system else current_user.id

    role, err = RBACService.create_role(
        user_id=role_user_id,
        name=data.get('name', '').strip(),
        code=code,
        description=data.get('description', '').strip(),
        permission_codes=data.get('permissions', []),
        is_system=is_system,
    )
    if err:
        return jsonify({'success': False, 'msg': err}), 400
    return jsonify({'success': True, 'data': role.to_dict()})


@rbac_bp.route('/roles/<int:role_id>', methods=['PUT'])
@login_required
@require_permission('role.write')
def update_role(role_id):
    """更新角色信息和权限"""
    role = Role.query.get_or_404(role_id)
    data = request.get_json() or {}
    if data.get('name'):
        role.name = data['name'].strip()
    if data.get('description') is not None:
        role.description = data['description'].strip()
    if 'is_enabled' in data:
        role.is_enabled = bool(data['is_enabled'])
    if 'permissions' in data:
        RBACService.update_role_permissions(role_id, data['permissions'])
    else:
        db.session.commit()
    return jsonify({'success': True, 'data': role.to_dict()})


@rbac_bp.route('/roles/<int:role_id>', methods=['DELETE'])
@login_required
@require_permission('role.delete')
def delete_role(role_id):
    """删除角色"""
    role = Role.query.get_or_404(role_id)
    if role.is_system:
        return jsonify({'success': False, 'msg': '系统内置角色不可删除'}), 400
    db.session.delete(role)
    db.session.commit()
    return jsonify({'success': True})


@rbac_bp.route('/users', methods=['GET'])
@login_required
@require_permission('user.read')
def list_users_with_roles():
    """列出所有用户及其角色（管理用）"""
    from models.database import User
    users = User.query.order_by(User.id).all()
    out = []
    for u in users:
        roles = RBACService.get_user_roles(u.id)
        perms = RBACService.get_user_permissions(u.id) if u.is_admin or current_user.is_admin else set()
        out.append({
            'id': u.id,
            'username': u.username,
            'is_admin': u.is_admin,
            'is_active': u.is_active,
            'last_login_at': u.last_login_at.isoformat() if u.last_login_at else None,
            'created_at': u.created_at.isoformat() if u.created_at else None,
            'roles': [{'id': r.id, 'code': r.code, 'name': r.name} for r in roles],
            'permission_count': len(perms),
        })
    return jsonify({'success': True, 'data': out})


@rbac_bp.route('/users/<int:user_id>/roles', methods=['GET'])
@login_required
@require_permission('user.read')
def get_user_roles(user_id):
    """获取用户的角色"""
    roles = RBACService.get_user_roles(user_id)
    return jsonify({'success': True, 'data': [r.to_dict() for r in roles]})


@rbac_bp.route('/users/<int:user_id>/roles', methods=['POST'])
@login_required
@require_permission('user.write')
def assign_role(user_id):
    """给用户分配角色"""
    data = request.get_json() or {}
    role_id = data.get('role_id')
    if not role_id:
        return jsonify({'success': False, 'msg': '缺少 role_id'}), 400
    User.query.get_or_404(user_id)
    success = RBACService.assign_role_to_user(user_id, role_id)
    if not success:
        return jsonify({'success': False, 'msg': '该用户已拥有此角色'}), 400
    return jsonify({'success': True})


@rbac_bp.route('/users/<int:user_id>/roles/<int:role_id>', methods=['DELETE'])
@login_required
@require_permission('user.write')
def unassign_role(user_id, role_id):
    """移除用户的角色"""
    success = RBACService.remove_role_from_user(user_id, role_id)
    return jsonify({'success': True, 'data': {'removed': success}})


@rbac_bp.route('/users/<int:user_id>/permissions', methods=['GET'])
@login_required
@require_permission('user.read')
def get_user_perms(user_id):
    """获取用户的所有有效权限"""
    perms = RBACService.get_user_permissions(user_id)
    return jsonify({'success': True, 'data': sorted(list(perms))})


@rbac_bp.route('/my-permissions', methods=['GET'])
@login_required
def my_permissions():
    """获取当前登录用户的所有权限（前端用于按钮控制）"""
    perms = RBACService.get_user_permissions(current_user.id)
    return jsonify({'success': True, 'data': sorted(list(perms))})
