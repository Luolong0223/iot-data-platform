"""
多租户隔离路由
Multi-Tenant Isolation Routes
"""
import logging
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.tenant_service import TenantService, DepartmentService, MemberService, QuotaService

logger = logging.getLogger(__name__)

tenant_bp = Blueprint('tenant', __name__, url_prefix='/api/tenant')


# ========================================================================
# 组织管理
# ========================================================================

@tenant_bp.route('/organizations', methods=['POST'])
@login_required
def create_organization():
    """创建组织"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        name = data.get('name')
        if not name:
            return jsonify({'success': False, 'message': '缺少组织名称'}), 400
        
        org = TenantService.create_organization(
            name=name,
            admin_user_id=current_user.id,
            org_type=data.get('org_type', 'team'),
            description=data.get('description'),
            max_users=data.get('max_users', 10),
            max_devices=data.get('max_devices', 100),
            max_storage_mb=data.get('max_storage_mb', 1024),
        )
        
        return jsonify({
            'success': True,
            'message': '组织创建成功',
            'organization': org.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"创建组织失败: {e}")
        return jsonify({'success': False, 'message': '创建组织失败'}), 500


@tenant_bp.route('/organizations/<int:org_id>', methods=['PUT'])
@login_required
def update_organization(org_id):
    """更新组织"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        org = TenantService.update_organization(
            org_id=org_id,
            user_id=current_user.id,
            **data
        )
        
        return jsonify({
            'success': True,
            'message': '组织更新成功',
            'organization': org.to_dict()
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"更新组织失败: {e}")
        return jsonify({'success': False, 'message': '更新组织失败'}), 500


@tenant_bp.route('/organizations/<int:org_id>', methods=['DELETE'])
@login_required
def delete_organization(org_id):
    """删除组织"""
    try:
        TenantService.delete_organization(org_id, current_user.id)
        
        return jsonify({
            'success': True,
            'message': '组织删除成功'
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"删除组织失败: {e}")
        return jsonify({'success': False, 'message': '删除组织失败'}), 500


@tenant_bp.route('/organizations/<int:org_id>', methods=['GET'])
@login_required
def get_organization(org_id):
    """获取组织详情"""
    try:
        org = TenantService.get_organization(org_id)
        if not org:
            return jsonify({'success': False, 'message': '组织不存在'}), 404
        
        return jsonify({
            'success': True,
            'organization': org.to_dict()
        })
        
    except Exception as e:
        logger.error(f"获取组织详情失败: {e}")
        return jsonify({'success': False, 'message': '获取组织详情失败'}), 500


@tenant_bp.route('/organizations', methods=['GET'])
@login_required
def list_organizations():
    """获取组织列表"""
    try:
        enabled = request.args.get('enabled')
        if enabled is not None:
            enabled = enabled.lower() == 'true'
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        result = TenantService.list_organizations(
            user_id=current_user.id,
            enabled=enabled,
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'success': True,
            'organizations': result['organizations'],
            'pagination': {
                'total': result['total'],
                'page': result['page'],
                'per_page': result['per_page'],
                'pages': result['pages']
            }
        })
        
    except Exception as e:
        logger.error(f"获取组织列表失败: {e}")
        return jsonify({'success': False, 'message': '获取组织列表失败'}), 500


# ========================================================================
# 部门管理
# ========================================================================

@tenant_bp.route('/organizations/<int:org_id>/departments', methods=['POST'])
@login_required
def create_department(org_id):
    """创建部门"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        name = data.get('name')
        if not name:
            return jsonify({'success': False, 'message': '缺少部门名称'}), 400
        
        dept = DepartmentService.create_department(
            org_id=org_id,
            name=name,
            user_id=current_user.id,
            description=data.get('description'),
            parent_id=data.get('parent_id'),
        )
        
        return jsonify({
            'success': True,
            'message': '部门创建成功',
            'department': dept.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"创建部门失败: {e}")
        return jsonify({'success': False, 'message': '创建部门失败'}), 500


@tenant_bp.route('/departments/<int:dept_id>', methods=['PUT'])
@login_required
def update_department(dept_id):
    """更新部门"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        dept = DepartmentService.update_department(
            dept_id=dept_id,
            user_id=current_user.id,
            **data
        )
        
        return jsonify({
            'success': True,
            'message': '部门更新成功',
            'department': dept.to_dict()
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"更新部门失败: {e}")
        return jsonify({'success': False, 'message': '更新部门失败'}), 500


@tenant_bp.route('/departments/<int:dept_id>', methods=['DELETE'])
@login_required
def delete_department(dept_id):
    """删除部门"""
    try:
        DepartmentService.delete_department(dept_id, current_user.id)
        
        return jsonify({
            'success': True,
            'message': '部门删除成功'
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"删除部门失败: {e}")
        return jsonify({'success': False, 'message': '删除部门失败'}), 500


@tenant_bp.route('/organizations/<int:org_id>/departments', methods=['GET'])
@login_required
def list_departments(org_id):
    """获取部门列表"""
    try:
        parent_id = request.args.get('parent_id', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        result = DepartmentService.list_departments(
            org_id=org_id,
            parent_id=parent_id,
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'success': True,
            'departments': result['departments'],
            'pagination': {
                'total': result['total'],
                'page': result['page'],
                'per_page': result['per_page'],
                'pages': result['pages']
            }
        })
        
    except Exception as e:
        logger.error(f"获取部门列表失败: {e}")
        return jsonify({'success': False, 'message': '获取部门列表失败'}), 500


# ========================================================================
# 成员管理
# ========================================================================

@tenant_bp.route('/organizations/<int:org_id>/members', methods=['POST'])
@login_required
def add_member(org_id):
    """添加成员"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '缺少用户ID'}), 400
        
        member = MemberService.add_member(
            org_id=org_id,
            user_id=user_id,
            admin_user_id=current_user.id,
            role=data.get('role', 'member'),
            department_id=data.get('department_id'),
        )
        
        return jsonify({
            'success': True,
            'message': '成员添加成功',
            'member': member.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"添加成员失败: {e}")
        return jsonify({'success': False, 'message': '添加成员失败'}), 500


@tenant_bp.route('/organizations/<int:org_id>/members/<int:user_id>', methods=['DELETE'])
@login_required
def remove_member(org_id, user_id):
    """移除成员"""
    try:
        MemberService.remove_member(
            org_id=org_id,
            user_id=user_id,
            admin_user_id=current_user.id,
        )
        
        return jsonify({
            'success': True,
            'message': '成员移除成功'
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"移除成员失败: {e}")
        return jsonify({'success': False, 'message': '移除成员失败'}), 500


@tenant_bp.route('/organizations/<int:org_id>/members/<int:user_id>/role', methods=['PUT'])
@login_required
def update_member_role(org_id, user_id):
    """更新成员角色"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        role = data.get('role')
        if not role:
            return jsonify({'success': False, 'message': '缺少角色'}), 400
        
        member = MemberService.update_member_role(
            org_id=org_id,
            user_id=user_id,
            admin_user_id=current_user.id,
            role=role,
        )
        
        return jsonify({
            'success': True,
            'message': '成员角色更新成功',
            'member': member.to_dict()
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"更新成员角色失败: {e}")
        return jsonify({'success': False, 'message': '更新成员角色失败'}), 500


@tenant_bp.route('/organizations/<int:org_id>/members', methods=['GET'])
@login_required
def list_members(org_id):
    """获取成员列表"""
    try:
        department_id = request.args.get('department_id', type=int)
        role = request.args.get('role')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        result = MemberService.list_members(
            org_id=org_id,
            department_id=department_id,
            role=role,
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'success': True,
            'members': result['members'],
            'pagination': {
                'total': result['total'],
                'page': result['page'],
                'per_page': result['per_page'],
                'pages': result['pages']
            }
        })
        
    except Exception as e:
        logger.error(f"获取成员列表失败: {e}")
        return jsonify({'success': False, 'message': '获取成员列表失败'}), 500


# ========================================================================
# 配额管理
# ========================================================================

@tenant_bp.route('/organizations/<int:org_id>/quota', methods=['GET'])
@login_required
def get_quota_status(org_id):
    """获取配额状态"""
    try:
        status = QuotaService.get_quota_status(org_id)
        
        return jsonify({
            'success': True,
            'quota': status
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"获取配额状态失败: {e}")
        return jsonify({'success': False, 'message': '获取配额状态失败'}), 500


@tenant_bp.route('/organizations/<int:org_id>/quota', methods=['PUT'])
@login_required
def update_quota(org_id):
    """更新配额限制"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        org = QuotaService.update_quota(
            org_id=org_id,
            admin_user_id=current_user.id,
            max_users=data.get('max_users'),
            max_devices=data.get('max_devices'),
            max_storage_mb=data.get('max_storage_mb'),
        )
        
        return jsonify({
            'success': True,
            'message': '配额更新成功',
            'organization': org.to_dict()
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"更新配额失败: {e}")
        return jsonify({'success': False, 'message': '更新配额失败'}), 500


@tenant_bp.route('/organizations/<int:org_id>/quota/check', methods=['POST'])
@login_required
def check_quota(org_id):
    """检查配额"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        resource_type = data.get('resource_type')
        amount = data.get('amount', 1.0)
        
        if not resource_type:
            return jsonify({'success': False, 'message': '缺少资源类型'}), 400
        
        has_quota = QuotaService.check_quota(org_id, resource_type, amount)
        
        return jsonify({
            'success': True,
            'has_quota': has_quota,
            'resource_type': resource_type,
            'amount': amount
        })
        
    except Exception as e:
        logger.error(f"检查配额失败: {e}")
        return jsonify({'success': False, 'message': '检查配额失败'}), 500
