"""
多租户隔离服务
Multi-Tenant Isolation Service
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from models.database import db, Organization, Department, OrganizationMember, QuotaUsage, User
from sqlalchemy import desc

logger = logging.getLogger(__name__)


class TenantService:
    """租户服务"""
    
    @staticmethod
    def create_organization(
        name: str,
        admin_user_id: int,
        org_type: str = 'team',
        description: Optional[str] = None,
        max_users: int = 10,
        max_devices: int = 100,
        max_storage_mb: int = 1024,
    ) -> Organization:
        """创建组织"""
        # 检查名称是否已存在
        existing = Organization.query.filter_by(name=name).first()
        if existing:
            raise ValueError(f"组织名称已存在: {name}")
        
        org = Organization(
            name=name,
            description=description,
            org_type=org_type,
            admin_user_id=admin_user_id,
            max_users=max_users,
            max_devices=max_devices,
            max_storage_mb=max_storage_mb,
            current_users=1,  # 管理员算一个用户
            enabled=True
        )
        
        db.session.add(org)
        db.session.flush()
        
        # 添加管理员为组织成员
        member = OrganizationMember(
            org_id=org.id,
            user_id=admin_user_id,
            role='admin',
            enabled=True
        )
        db.session.add(member)
        
        db.session.commit()
        
        logger.info(f"创建组织: {org.id}, 名称: {name}")
        return org
    
    @staticmethod
    def update_organization(
        org_id: int,
        user_id: int,
        **kwargs
    ) -> Organization:
        """更新组织"""
        org = Organization.query.filter_by(id=org_id).first()
        if not org:
            raise ValueError(f"组织不存在: {org_id}")
        
        # 检查权限
        if not TenantService._is_org_admin(org_id, user_id):
            raise ValueError("无权限更新组织信息")
        
        for key, value in kwargs.items():
            if hasattr(org, key) and key not in ['id', 'created_at']:
                setattr(org, key, value)
        
        db.session.commit()
        
        logger.info(f"更新组织: {org.id}")
        return org
    
    @staticmethod
    def delete_organization(org_id: int, user_id: int) -> bool:
        """删除组织"""
        org = Organization.query.filter_by(id=org_id).first()
        if not org:
            raise ValueError(f"组织不存在: {org_id}")
        
        # 检查权限
        if not TenantService._is_org_admin(org_id, user_id):
            raise ValueError("无权限删除组织")
        
        db.session.delete(org)
        db.session.commit()
        
        logger.info(f"删除组织: {org.id}")
        return True
    
    @staticmethod
    def get_organization(org_id: int) -> Optional[Organization]:
        """获取组织详情"""
        return Organization.query.filter_by(id=org_id).first()
    
    @staticmethod
    def list_organizations(
        user_id: Optional[int] = None,
        enabled: Optional[bool] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """获取组织列表"""
        query = Organization.query
        
        if user_id:
            # 只返回用户所属的组织
            org_ids = db.session.query(OrganizationMember.org_id).filter_by(
                user_id=user_id, enabled=True
            ).subquery()
            query = query.filter(Organization.id.in_(org_ids))
        
        if enabled is not None:
            query = query.filter_by(enabled=enabled)
        
        query = query.order_by(desc(Organization.created_at))
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'organizations': [org.to_dict() for org in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    
    @staticmethod
    def _is_org_admin(org_id: int, user_id: int) -> bool:
        """检查用户是否是组织管理员"""
        member = OrganizationMember.query.filter_by(
            org_id=org_id, user_id=user_id, enabled=True
        ).first()
        return member and member.role in ['admin', 'manager']


class DepartmentService:
    """部门服务"""
    
    @staticmethod
    def create_department(
        org_id: int,
        name: str,
        user_id: int,
        description: Optional[str] = None,
        parent_id: Optional[int] = None,
    ) -> Department:
        """创建部门"""
        # 检查权限
        if not TenantService._is_org_admin(org_id, user_id):
            raise ValueError("无权限创建部门")
        
        dept = Department(
            org_id=org_id,
            name=name,
            description=description,
            parent_id=parent_id,
            enabled=True
        )
        
        db.session.add(dept)
        db.session.commit()
        
        logger.info(f"创建部门: {dept.id}, 名称: {name}")
        return dept
    
    @staticmethod
    def update_department(
        dept_id: int,
        user_id: int,
        **kwargs
    ) -> Department:
        """更新部门"""
        dept = Department.query.filter_by(id=dept_id).first()
        if not dept:
            raise ValueError(f"部门不存在: {dept_id}")
        
        # 检查权限
        if not TenantService._is_org_admin(dept.org_id, user_id):
            raise ValueError("无权限更新部门")
        
        for key, value in kwargs.items():
            if hasattr(dept, key) and key not in ['id', 'created_at', 'org_id']:
                setattr(dept, key, value)
        
        db.session.commit()
        
        logger.info(f"更新部门: {dept.id}")
        return dept
    
    @staticmethod
    def delete_department(dept_id: int, user_id: int) -> bool:
        """删除部门"""
        dept = Department.query.filter_by(id=dept_id).first()
        if not dept:
            raise ValueError(f"部门不存在: {dept_id}")
        
        # 检查权限
        if not TenantService._is_org_admin(dept.org_id, user_id):
            raise ValueError("无权限删除部门")
        
        db.session.delete(dept)
        db.session.commit()
        
        logger.info(f"删除部门: {dept.id}")
        return True
    
    @staticmethod
    def list_departments(
        org_id: int,
        parent_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """获取部门列表"""
        query = Department.query.filter_by(org_id=org_id)
        
        if parent_id is not None:
            query = query.filter_by(parent_id=parent_id)
        
        query = query.order_by(Department.name)
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'departments': [dept.to_dict() for dept in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }


class MemberService:
    """成员服务"""
    
    @staticmethod
    def add_member(
        org_id: int,
        user_id: int,
        admin_user_id: int,
        role: str = 'member',
        department_id: Optional[int] = None,
    ) -> OrganizationMember:
        """添加成员"""
        # 检查权限
        if not TenantService._is_org_admin(org_id, admin_user_id):
            raise ValueError("无权限添加成员")
        
        # 检查配额
        org = Organization.query.filter_by(id=org_id).first()
        if not org:
            raise ValueError(f"组织不存在: {org_id}")
        
        if org.current_users >= org.max_users:
            raise ValueError(f"已达到用户配额上限: {org.max_users}")
        
        # 检查是否已是成员
        existing = OrganizationMember.query.filter_by(org_id=org_id, user_id=user_id).first()
        if existing:
            raise ValueError("用户已是组织成员")
        
        member = OrganizationMember(
            org_id=org_id,
            user_id=user_id,
            role=role,
            department_id=department_id,
            enabled=True
        )
        
        db.session.add(member)
        
        # 更新组织用户数
        org.current_users += 1
        
        db.session.commit()
        
        logger.info(f"添加成员: {member.id}, 组织: {org_id}, 用户: {user_id}")
        return member
    
    @staticmethod
    def remove_member(
        org_id: int,
        user_id: int,
        admin_user_id: int,
    ) -> bool:
        """移除成员"""
        # 检查权限
        if not TenantService._is_org_admin(org_id, admin_user_id):
            raise ValueError("无权限移除成员")
        
        member = OrganizationMember.query.filter_by(org_id=org_id, user_id=user_id).first()
        if not member:
            raise ValueError("用户不是组织成员")
        
        # 不能移除管理员
        if member.role == 'admin':
            raise ValueError("不能移除组织管理员")
        
        db.session.delete(member)
        
        # 更新组织用户数
        org = Organization.query.filter_by(id=org_id).first()
        org.current_users = max(0, org.current_users - 1)
        
        db.session.commit()
        
        logger.info(f"移除成员: 组织: {org_id}, 用户: {user_id}")
        return True
    
    @staticmethod
    def update_member_role(
        org_id: int,
        user_id: int,
        admin_user_id: int,
        role: str,
    ) -> OrganizationMember:
        """更新成员角色"""
        # 检查权限
        if not TenantService._is_org_admin(org_id, admin_user_id):
            raise ValueError("无权限更新成员角色")
        
        member = OrganizationMember.query.filter_by(org_id=org_id, user_id=user_id).first()
        if not member:
            raise ValueError("用户不是组织成员")
        
        member.role = role
        db.session.commit()
        
        logger.info(f"更新成员角色: 组织: {org_id}, 用户: {user_id}, 角色: {role}")
        return member
    
    @staticmethod
    def list_members(
        org_id: int,
        department_id: Optional[int] = None,
        role: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """获取成员列表"""
        query = OrganizationMember.query.filter_by(org_id=org_id, enabled=True)
        
        if department_id:
            query = query.filter_by(department_id=department_id)
        
        if role:
            query = query.filter_by(role=role)
        
        query = query.order_by(OrganizationMember.joined_at)
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'members': [m.to_dict() for m in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }


class QuotaService:
    """配额服务"""
    
    @staticmethod
    def check_quota(org_id: int, resource_type: str, amount: float = 1.0) -> bool:
        """检查配额是否足够"""
        org = Organization.query.filter_by(id=org_id).first()
        if not org:
            return False
        
        if resource_type == 'devices':
            return org.current_devices + amount <= org.max_devices
        elif resource_type == 'storage':
            return org.current_storage_mb + amount <= org.max_storage_mb
        elif resource_type == 'users':
            return org.current_users + amount <= org.max_users
        
        return True
    
    @staticmethod
    def update_usage(org_id: int, resource_type: str, delta: float) -> None:
        """更新使用量"""
        org = Organization.query.filter_by(id=org_id).first()
        if not org:
            return
        
        if resource_type == 'devices':
            org.current_devices = max(0, org.current_devices + delta)
        elif resource_type == 'storage':
            org.current_storage_mb = max(0, org.current_storage_mb + delta)
        elif resource_type == 'users':
            org.current_users = max(0, org.current_users + delta)
        
        db.session.commit()
        
        logger.info(f"更新配额使用: 组织: {org_id}, 资源: {resource_type}, 变化: {delta}")
    
    @staticmethod
    def get_quota_status(org_id: int) -> Dict[str, Any]:
        """获取配额状态"""
        org = Organization.query.filter_by(id=org_id).first()
        if not org:
            raise ValueError(f"组织不存在: {org_id}")
        
        return {
            'users': {
                'used': org.current_users,
                'limit': org.max_users,
                'percentage': round(org.current_users / org.max_users * 100, 2) if org.max_users > 0 else 0
            },
            'devices': {
                'used': org.current_devices,
                'limit': org.max_devices,
                'percentage': round(org.current_devices / org.max_devices * 100, 2) if org.max_devices > 0 else 0
            },
            'storage': {
                'used': org.current_storage_mb,
                'limit': org.max_storage_mb,
                'percentage': round(org.current_storage_mb / org.max_storage_mb * 100, 2) if org.max_storage_mb > 0 else 0
            }
        }
    
    @staticmethod
    def update_quota(
        org_id: int,
        admin_user_id: int,
        max_users: Optional[int] = None,
        max_devices: Optional[int] = None,
        max_storage_mb: Optional[int] = None,
    ) -> Organization:
        """更新配额限制"""
        org = Organization.query.filter_by(id=org_id).first()
        if not org:
            raise ValueError(f"组织不存在: {org_id}")
        
        # 检查权限
        if not TenantService._is_org_admin(org_id, admin_user_id):
            raise ValueError("无权限更新配额")
        
        if max_users is not None:
            org.max_users = max_users
        if max_devices is not None:
            org.max_devices = max_devices
        if max_storage_mb is not None:
            org.max_storage_mb = max_storage_mb
        
        db.session.commit()
        
        logger.info(f"更新配额: 组织: {org.id}")
        return org
