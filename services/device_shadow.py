"""
设备影子服务 (Device Shadow Service)
管理设备的期望状态和报告状态，支持离线状态同步
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from models.database import db, DeviceShadow, ShadowHistory, Device
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class DeviceShadowService:
    """设备影子服务类"""

    @staticmethod
    def get_or_create_shadow(device_id: int, user_id: int) -> DeviceShadow:
        """获取或创建设备影子"""
        shadow = DeviceShadow.query.filter_by(device_id=device_id).first()
        if not shadow:
            shadow = DeviceShadow(
                device_id=device_id,
                user_id=user_id,
                desired_state='{}',
                reported_state='{}',
                desired_version=1,
                reported_version=1,
                sync_status='pending',
                is_online=False
            )
            db.session.add(shadow)
            db.session.commit()
            logger.info(f"Created shadow for device {device_id}")
        return shadow

    @staticmethod
    def get_shadow(device_id: int) -> Optional[DeviceShadow]:
        """获取设备影子"""
        return DeviceShadow.query.filter_by(device_id=device_id).first()

    @staticmethod
    def update_desired_state(device_id: int, user_id: int, state: Dict[str, Any], 
                            operator: str = 'user') -> Dict[str, Any]:
        """
        更新期望状态 (desired state)
        当设备离线时，设置期望状态，设备上线后同步
        """
        try:
            shadow = DeviceShadowService.get_or_create_shadow(device_id, user_id)
            
            # 记录历史
            old_state = shadow.desired_state
            ShadowHistory(
                shadow_id=shadow.id,
                device_id=device_id,
                user_id=user_id,
                change_type='desired_update',
                old_state=old_state,
                new_state=json.dumps(state, ensure_ascii=False),
                version=shadow.desired_version + 1,
                operator=operator
            )
            
            # 更新状态
            shadow.desired_state = json.dumps(state, ensure_ascii=False)
            shadow.desired_version += 1
            shadow.desired_updated_at = datetime.utcnow()
            shadow.sync_status = 'pending'  # 标记为待同步
            
            db.session.commit()
            logger.info(f"Updated desired state for device {device_id}, version {shadow.desired_version}")
            
            return {
                'success': True,
                'shadow': shadow.to_dict(),
                'message': '期望状态已更新，等待设备同步'
            }
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to update desired state: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def update_reported_state(device_id: int, user_id: int, state: Dict[str, Any],
                             operator: str = 'device') -> Dict[str, Any]:
        """
        更新报告状态 (reported state)
        设备上报当前状态
        """
        try:
            shadow = DeviceShadowService.get_or_create_shadow(device_id, user_id)
            
            # 记录历史
            old_state = shadow.reported_state
            ShadowHistory(
                shadow_id=shadow.id,
                device_id=device_id,
                user_id=user_id,
                change_type='reported_update',
                old_state=old_state,
                new_state=json.dumps(state, ensure_ascii=False),
                version=shadow.reported_version + 1,
                operator=operator
            )
            
            # 更新状态
            shadow.reported_state = json.dumps(state, ensure_ascii=False)
            shadow.reported_version += 1
            shadow.reported_updated_at = datetime.utcnow()
            
            # 检查是否与期望状态一致
            desired = json.loads(shadow.desired_state) if shadow.desired_state else {}
            if desired == state:
                shadow.sync_status = 'synced'
                shadow.last_sync_at = datetime.utcnow()
                shadow.sync_error = None
            
            db.session.commit()
            logger.info(f"Updated reported state for device {device_id}, version {shadow.reported_version}")
            
            return {
                'success': True,
                'shadow': shadow.to_dict(),
                'message': '报告状态已更新'
            }
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to update reported state: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def sync_shadow(device_id: int, user_id: int) -> Dict[str, Any]:
        """
        同步设备影子
        当设备上线时调用，将期望状态下发给设备
        """
        try:
            shadow = DeviceShadowService.get_or_create_shadow(device_id, user_id)
            
            desired = json.loads(shadow.desired_state) if shadow.desired_state else {}
            reported = json.loads(shadow.reported_state) if shadow.reported_state else {}
            
            # 如果期望状态和报告状态一致，无需同步
            if desired == reported:
                shadow.sync_status = 'synced'
                shadow.last_sync_at = datetime.utcnow()
                db.session.commit()
                return {
                    'success': True,
                    'need_sync': False,
                    'message': '设备状态已同步，无需更新'
                }
            
            # 标记为同步中
            shadow.sync_status = 'syncing'
            db.session.commit()
            
            # 记录同步历史
            ShadowHistory(
                shadow_id=shadow.id,
                device_id=device_id,
                user_id=user_id,
                change_type='sync',
                old_state=shadow.reported_state,
                new_state=shadow.desired_state,
                version=shadow.desired_version,
                operator='system'
            )
            
            # 实际场景中这里会通过 MQTT/WebSocket 下发命令给设备
            # 这里模拟同步成功
            shadow.reported_state = shadow.desired_state
            shadow.reported_version = shadow.desired_version
            shadow.reported_updated_at = datetime.utcnow()
            shadow.sync_status = 'synced'
            shadow.last_sync_at = datetime.utcnow()
            shadow.sync_error = None
            
            db.session.commit()
            logger.info(f"Synced shadow for device {device_id}")
            
            return {
                'success': True,
                'need_sync': True,
                'shadow': shadow.to_dict(),
                'message': '设备影子已同步'
            }
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to sync shadow: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_shadow_history(device_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """获取设备影子变更历史"""
        histories = ShadowHistory.query.filter_by(device_id=device_id)\
            .order_by(ShadowHistory.created_at.desc())\
            .limit(limit)\
            .all()
        return [h.to_dict() for h in histories]

    @staticmethod
    def get_pending_shadows(user_id: int) -> List[DeviceShadow]:
        """获取待同步的设备影子列表"""
        return DeviceShadow.query.filter_by(
            user_id=user_id,
            sync_status='pending'
        ).all()

    @staticmethod
    def batch_sync(user_id: int) -> Dict[str, Any]:
        """批量同步所有待同步的设备影子"""
        pending = DeviceShadowService.get_pending_shadows(user_id)
        results = []
        for shadow in pending:
            result = DeviceShadowService.sync_shadow(shadow.device_id, user_id)
            results.append({
                'device_id': shadow.device_id,
                'device_name': shadow.device.name if shadow.device else None,
                'result': result
            })
        
        return {
            'success': True,
            'total': len(pending),
            'results': results
        }

    @staticmethod
    def delete_shadow(device_id: int) -> Dict[str, Any]:
        """删除设备影子"""
        try:
            shadow = DeviceShadow.query.filter_by(device_id=device_id).first()
            if shadow:
                db.session.delete(shadow)
                db.session.commit()
                logger.info(f"Deleted shadow for device {device_id}")
                return {'success': True, 'message': '设备影子已删除'}
            return {'success': False, 'error': '设备影子不存在'}
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to delete shadow: {e}")
            return {'success': False, 'error': str(e)}
