"""
RBAC 角色权限服务
实现细粒度的资源-操作权限控制
"""
from functools import wraps
from flask import jsonify, g
from flask_login import current_user
from models.database import db, Role, Permission, RolePermission, UserRole


# 预定义所有权限
DEFAULT_PERMISSIONS = [
    # 设备权限
    ('device.read', '查看设备', 'device', 'read', '查看设备列表和详情'),
    ('device.write', '编辑设备', 'device', 'write', '创建/修改设备'),
    ('device.delete', '删除设备', 'device', 'delete', '删除设备'),
    ('device.control', '控制设备', 'device', 'control', '向设备发送指令'),
    # 告警权限
    ('alarm.read', '查看告警', 'alarm', 'read', '查看告警记录'),
    ('alarm.write', '处理告警', 'alarm', 'write', '确认/处理告警'),
    ('alarm.delete', '删除告警', 'alarm', 'delete', '删除告警'),
    # 用户权限
    ('user.read', '查看用户', 'user', 'read', '查看用户列表'),
    ('user.write', '编辑用户', 'user', 'write', '创建/修改用户'),
    ('user.delete', '删除用户', 'user', 'delete', '删除用户'),
    # 角色权限
    ('role.read', '查看角色', 'role', 'read', '查看角色列表'),
    ('role.write', '编辑角色', 'role', 'write', '创建/修改角色'),
    ('role.delete', '删除角色', 'role', 'delete', '删除角色'),
    # 报表权限
    ('report.read', '查看报表', 'report', 'read', '查看统计报表'),
    ('report.export', '导出报表', 'report', 'export', '导出 Excel 报表'),
    # 系统权限
    ('system.config', '系统配置', 'system', 'config', '系统配置管理'),
    ('system.audit', '审计日志', 'system', 'audit', '查看审计日志'),
]

# 预定义角色
DEFAULT_ROLES = {
    'admin': {
        'name': '系统管理员',
        'description': '拥有所有权限',
        'permissions': '*'  # 全部权限
    },
    'operator': {
        'name': '操作员',
        'description': '可查看/操作设备和告警',
        'permissions': [
            'device.read', 'device.write', 'device.control',
            'alarm.read', 'alarm.write',
            'report.read', 'report.export'
        ]
    },
    'viewer': {
        'name': '观察者',
        'description': '只读权限',
        'permissions': [
            'device.read', 'alarm.read', 'report.read', 'role.read', 'user.read'
        ]
    }
}


class RBACService:
    """RBAC 权限服务"""

    @staticmethod
    def init_permissions():
        """初始化权限表、默认角色、并把所有用户绑定到对应角色"""
        for code, name, resource, action, desc in DEFAULT_PERMISSIONS:
            perm = Permission.query.filter_by(code=code).first()
            if not perm:
                perm = Permission(code=code, name=name, resource=resource, action=action, description=desc)
                db.session.add(perm)
        db.session.commit()

        # 1) 创建默认角色（admin / operator / viewer）
        default_role_map = {}  # code -> role.id
        for code, info in DEFAULT_ROLES.items():
            role = Role.query.filter_by(code=code, user_id=None).first()
            if not role:
                role = Role(
                    user_id=None,
                    name=info['name'],
                    code=code,
                    description=info['description'],
                    is_system=True,
                    is_enabled=True,
                )
                db.session.add(role)
                db.session.flush()
            default_role_map[code] = role.id

            # 绑定权限
            if info['permissions'] == '*':
                perm_ids = [p.id for p in Permission.query.all()]
            else:
                perm_ids = [p.id for p in Permission.query.filter(Permission.code.in_(info['permissions'])).all()]
            RolePermission.query.filter_by(role_id=role.id).delete()
            for pid in perm_ids:
                db.session.add(RolePermission(role_id=role.id, permission_id=pid))
        db.session.commit()

        # 2) 给所有现有用户绑定默认角色（admin 用户 → admin 角色，其他用户 → viewer）
        from models.database import User
        users = User.query.all()
        for u in users:
            existing_codes = {ur.role.code for ur in u.user_roles if ur.role and ur.role.code}
            if u.is_admin and 'admin' not in existing_codes:
                db.session.add(UserRole(user_id=u.id, role_id=default_role_map['admin']))
            elif not u.is_admin and 'viewer' not in existing_codes:
                db.session.add(UserRole(user_id=u.id, role_id=default_role_map['viewer']))
        db.session.commit()
        return Permission.query.count()

    @staticmethod
    def init_default_roles():
        """为新用户创建默认角色"""
        return DEFAULT_ROLES

    @staticmethod
    def create_role(user_id, name, code, description, permission_codes, is_system=False):
        """创建角色并分配权限"""
        # 防止重复：user_id=None（系统角色）按 code 全局唯一；否则按 (user_id, code) 唯一
        if user_id is None:
            existing = Role.query.filter_by(user_id=None, code=code).first()
        else:
            existing = Role.query.filter_by(user_id=user_id, code=code).first()
        if existing:
            return None, '角色代码已存在'

        role = Role(
            user_id=user_id, name=name, code=code,
            description=description, is_system=is_system, is_enabled=True
        )
        db.session.add(role)
        db.session.flush()  # 获取 role.id

        for pcode in permission_codes:
            perm = Permission.query.filter_by(code=pcode).first()
            if perm:
                rp = RolePermission(role_id=role.id, permission_id=perm.id)
                db.session.add(rp)

        db.session.commit()
        return role, None

    @staticmethod
    def get_user_permissions(user_id):
        """获取用户所有有效权限"""
        user_role_ids = [ur.role_id for ur in UserRole.query.filter_by(user_id=user_id).all()]
        if not user_role_ids:
            return set()

        perms = db.session.query(Permission.code).join(
            RolePermission, RolePermission.permission_id == Permission.id
        ).join(
            Role, Role.id == RolePermission.role_id
        ).join(
            UserRole, UserRole.role_id == Role.id
        ).filter(
            UserRole.user_id == user_id,
            Role.is_enabled == True
        ).all()
        return {p[0] for p in perms}

    @staticmethod
    def has_permission(user_id, permission_code):
        """检查用户是否拥有指定权限"""
        perms = RBACService.get_user_permissions(user_id)
        return permission_code in perms

    @staticmethod
    def assign_role_to_user(user_id, role_id):
        """给用户分配角色"""
        existing = UserRole.query.filter_by(user_id=user_id, role_id=role_id).first()
        if existing:
            return False
        ur = UserRole(user_id=user_id, role_id=role_id)
        db.session.add(ur)
        db.session.commit()
        return True

    @staticmethod
    def remove_role_from_user(user_id, role_id):
        """移除用户的角色"""
        ur = UserRole.query.filter_by(user_id=user_id, role_id=role_id).first()
        if ur:
            db.session.delete(ur)
            db.session.commit()
            return True
        return False

    @staticmethod
    def get_user_roles(user_id):
        """获取用户的所有角色"""
        role_ids = [ur.role_id for ur in UserRole.query.filter_by(user_id=user_id).all()]
        if not role_ids:
            return []
        return Role.query.filter(Role.id.in_(role_ids), Role.is_enabled == True).all()

    @staticmethod
    def update_role_permissions(role_id, permission_codes):
        """更新角色的权限列表"""
        RolePermission.query.filter_by(role_id=role_id).delete()
        for pcode in permission_codes:
            perm = Permission.query.filter_by(code=pcode).first()
            if perm:
                rp = RolePermission(role_id=role_id, permission_id=perm.id)
                db.session.add(rp)
        db.session.commit()


def require_permission(permission_code):
    """权限装饰器 - 用于路由函数"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'success': False, 'msg': '未登录'}), 401
            if current_user.is_admin:
                return f(*args, **kwargs)
            if not RBACService.has_permission(current_user.id, permission_code):
                return jsonify({'success': False, 'msg': f'无权限: {permission_code}'}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator
