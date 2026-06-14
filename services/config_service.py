"""
配置中心服务
Configuration Center Service
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from models.database import db, DynamicConfig, ConfigVersion
from sqlalchemy import desc

logger = logging.getLogger(__name__)


class ConfigService:
    """配置服务"""
    
    @staticmethod
    def create_config(
        user_id: int,
        config_key: str,
        config_value: Any,
        value_type: str = 'string',
        description: Optional[str] = None,
        group_name: str = 'default',
        encrypted: bool = False,
    ) -> DynamicConfig:
        """创建配置"""
        # 检查是否已存在
        existing = DynamicConfig.query.filter_by(
            user_id=user_id, config_key=config_key
        ).first()
        if existing:
            raise ValueError(f"配置已存在: {config_key}")
        
        config = DynamicConfig(
            user_id=user_id,
            config_key=config_key,
            config_value=json.dumps(config_value),
            value_type=value_type,
            description=description,
            group_name=group_name,
            encrypted=encrypted,
            enabled=True,
            version=1
        )
        
        db.session.add(config)
        db.session.flush()
        
        # 创建初始版本记录
        version = ConfigVersion(
            config_id=config.id,
            user_id=user_id,
            version=1,
            config_value=json.dumps(config_value),
            change_note='初始创建',
            operator=str(user_id)
        )
        db.session.add(version)
        
        db.session.commit()
        
        logger.info(f"创建配置: {config.id}, key: {config_key}")
        return config
    
    @staticmethod
    def update_config(
        config_id: int,
        user_id: int,
        config_value: Any,
        change_note: Optional[str] = None,
    ) -> DynamicConfig:
        """更新配置"""
        config = DynamicConfig.query.filter_by(id=config_id, user_id=user_id).first()
        if not config:
            raise ValueError(f"配置不存在: {config_id}")
        
        # 更新配置值
        config.config_value = json.dumps(config_value)
        config.version += 1
        
        # 创建版本记录
        version = ConfigVersion(
            config_id=config.id,
            user_id=user_id,
            version=config.version,
            config_value=json.dumps(config_value),
            change_note=change_note or '配置更新',
            operator=str(user_id)
        )
        db.session.add(version)
        
        db.session.commit()
        
        logger.info(f"更新配置: {config.id}, version: {config.version}")
        return config
    
    @staticmethod
    def rollback_config(
        config_id: int,
        user_id: int,
        target_version: int,
        change_note: Optional[str] = None,
    ) -> DynamicConfig:
        """回滚配置到指定版本"""
        config = DynamicConfig.query.filter_by(id=config_id, user_id=user_id).first()
        if not config:
            raise ValueError(f"配置不存在: {config_id}")
        
        # 查找目标版本
        version_record = ConfigVersion.query.filter_by(
            config_id=config_id, version=target_version
        ).first()
        if not version_record:
            raise ValueError(f"版本不存在: {target_version}")
        
        # 回滚配置值
        config.config_value = version_record.config_value
        config.version += 1
        
        # 创建新版本记录
        new_version = ConfigVersion(
            config_id=config.id,
            user_id=user_id,
            version=config.version,
            config_value=version_record.config_value,
            change_note=change_note or f'回滚到版本 {target_version}',
            operator=str(user_id)
        )
        db.session.add(new_version)
        
        db.session.commit()
        
        logger.info(f"回滚配置: {config.id}, 到版本: {target_version}")
        return config
    
    @staticmethod
    def delete_config(config_id: int, user_id: int) -> bool:
        """删除配置"""
        config = DynamicConfig.query.filter_by(id=config_id, user_id=user_id).first()
        if not config:
            raise ValueError(f"配置不存在: {config_id}")
        
        db.session.delete(config)
        db.session.commit()
        
        logger.info(f"删除配置: {config.id}")
        return True
    
    @staticmethod
    def get_config(config_id: int, user_id: int) -> Optional[DynamicConfig]:
        """获取配置详情"""
        return DynamicConfig.query.filter_by(id=config_id, user_id=user_id).first()
    
    @staticmethod
    def get_config_by_key(user_id: int, config_key: str) -> Optional[DynamicConfig]:
        """通过 key 获取配置"""
        return DynamicConfig.query.filter_by(
            user_id=user_id, config_key=config_key, enabled=True
        ).first()
    
    @staticmethod
    def list_configs(
        user_id: int,
        group_name: Optional[str] = None,
        enabled: Optional[bool] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """获取配置列表"""
        query = DynamicConfig.query.filter_by(user_id=user_id)
        
        if group_name:
            query = query.filter_by(group_name=group_name)
        
        if enabled is not None:
            query = query.filter_by(enabled=enabled)
        
        query = query.order_by(DynamicConfig.config_key)
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'configs': [c.to_dict() for c in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    
    @staticmethod
    def list_versions(
        config_id: int,
        user_id: int,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """获取配置版本历史"""
        config = DynamicConfig.query.filter_by(id=config_id, user_id=user_id).first()
        if not config:
            raise ValueError(f"配置不存在: {config_id}")
        
        query = ConfigVersion.query.filter_by(config_id=config_id)
        query = query.order_by(desc(ConfigVersion.version))
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'versions': [v.to_dict() for v in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    
    @staticmethod
    def toggle_config(config_id: int, user_id: int, enabled: bool) -> DynamicConfig:
        """启用/禁用配置"""
        config = DynamicConfig.query.filter_by(id=config_id, user_id=user_id).first()
        if not config:
            raise ValueError(f"配置不存在: {config_id}")
        
        config.enabled = enabled
        db.session.commit()
        
        logger.info(f"配置状态变更: {config.id}, enabled: {enabled}")
        return config
    
    @staticmethod
    def batch_get_configs(user_id: int, config_keys: List[str]) -> Dict[str, Any]:
        """批量获取配置"""
        configs = DynamicConfig.query.filter(
            DynamicConfig.user_id == user_id,
            DynamicConfig.config_key.in_(config_keys),
            DynamicConfig.enabled == True
        ).all()
        
        result = {}
        for config in configs:
            try:
                result[config.config_key] = json.loads(config.config_value) if config.config_value else None
            except:
                result[config.config_key] = config.config_value
        
        return result
    
    @staticmethod
    def get_config_groups(user_id: int) -> List[str]:
        """获取配置分组列表"""
        groups = db.session.query(DynamicConfig.group_name).filter_by(
            user_id=user_id
        ).distinct().all()
        
        return [g[0] for g in groups]
