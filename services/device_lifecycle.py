"""
设备生命周期管理服务
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from models.database import db, Device, DeviceLifecycleEvent, DeviceMaintenanceRecord

logger = logging.getLogger(__name__)


class DeviceLifecycleService:
    """设备生命周期管理服务"""
    
    # 生命周期状态流转规则
    VALID_TRANSITIONS = {
        'registered': ['activated', 'retired'],
        'activated': ['deactivated', 'maintenance', 'retired'],
        'deactivated': ['activated', 'retired'],
        'maintenance': ['activated', 'retired'],
        'retired': ['decommissioned'],
        'decommissioned': []
    }
    
    @staticmethod
    def get_current_status(device_id: int) -> Optional[str]:
        """获取设备当前生命周期状态"""
        last_event = DeviceLifecycleEvent.query.filter_by(
            device_id=device_id
        ).order_by(DeviceLifecycleEvent.created_at.desc()).first()
        
        return last_event.event_type if last_event else 'registered'
    
    @staticmethod
    def can_transition(current_status: str, new_status: str) -> bool:
        """检查状态流转是否合法"""
        valid_next = DeviceLifecycleService.VALID_TRANSITIONS.get(current_status, [])
        return new_status in valid_next
    
    @staticmethod
    def register_device(device_id: int, user_id: int, operator: str = None, 
                       metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """注册设备"""
        device = Device.query.get(device_id)
        if not device:
            return {'success': False, 'message': '设备不存在'}
        
        # 检查是否已注册
        existing = DeviceLifecycleEvent.query.filter_by(
            device_id=device_id, event_type='registered'
        ).first()
        if existing:
            return {'success': False, 'message': '设备已注册'}
        
        event = DeviceLifecycleEvent(
            device_id=device_id,
            user_id=user_id,
            event_type='registered',
            description='设备注册',
            operator=operator or 'system',
            event_metadata=json.dumps(metadata or {})
        )
        db.session.add(event)
        db.session.commit()
        
        logger.info(f"Device {device_id} registered")
        return {'success': True, 'event': event.to_dict()}
    
    @staticmethod
    def activate_device(device_id: int, user_id: int, operator: str = None,
                       description: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """激活设备"""
        current_status = DeviceLifecycleService.get_current_status(device_id)
        
        if not DeviceLifecycleService.can_transition(current_status, 'activated'):
            return {'success': False, 'message': f'无法从 {current_status} 状态激活设备'}
        
        event = DeviceLifecycleEvent(
            device_id=device_id,
            user_id=user_id,
            event_type='activated',
            description=description or '设备激活',
            operator=operator or 'system',
            event_metadata=json.dumps(metadata or {})
        )
        db.session.add(event)
        
        # 更新设备在线状态
        device = Device.query.get(device_id)
        if device:
            device.is_online = True
        
        db.session.commit()
        
        logger.info(f"Device {device_id} activated")
        return {'success': True, 'event': event.to_dict()}
    
    @staticmethod
    def deactivate_device(device_id: int, user_id: int, operator: str = None,
                         description: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """停用设备"""
        current_status = DeviceLifecycleService.get_current_status(device_id)
        
        if not DeviceLifecycleService.can_transition(current_status, 'deactivated'):
            return {'success': False, 'message': f'无法从 {current_status} 状态停用设备'}
        
        event = DeviceLifecycleEvent(
            device_id=device_id,
            user_id=user_id,
            event_type='deactivated',
            description=description or '设备停用',
            operator=operator or 'system',
            event_metadata=json.dumps(metadata or {})
        )
        db.session.add(event)
        
        # 更新设备在线状态
        device = Device.query.get(device_id)
        if device:
            device.is_online = False
        
        db.session.commit()
        
        logger.info(f"Device {device_id} deactivated")
        return {'success': True, 'event': event.to_dict()}
    
    @staticmethod
    def start_maintenance(device_id: int, user_id: int, operator: str = None,
                         description: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """开始维护"""
        current_status = DeviceLifecycleService.get_current_status(device_id)
        
        if not DeviceLifecycleService.can_transition(current_status, 'maintenance'):
            return {'success': False, 'message': f'无法从 {current_status} 状态进入维护'}
        
        event = DeviceLifecycleEvent(
            device_id=device_id,
            user_id=user_id,
            event_type='maintenance',
            description=description or '设备进入维护模式',
            operator=operator or 'system',
            event_metadata=json.dumps(metadata or {})
        )
        db.session.add(event)
        
        # 更新设备在线状态
        device = Device.query.get(device_id)
        if device:
            device.is_online = False
        
        db.session.commit()
        
        logger.info(f"Device {device_id} entered maintenance mode")
        return {'success': True, 'event': event.to_dict()}
    
    @staticmethod
    def retire_device(device_id: int, user_id: int, operator: str = None,
                     description: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """退役设备"""
        current_status = DeviceLifecycleService.get_current_status(device_id)
        
        if not DeviceLifecycleService.can_transition(current_status, 'retired'):
            return {'success': False, 'message': f'无法从 {current_status} 状态退役设备'}
        
        event = DeviceLifecycleEvent(
            device_id=device_id,
            user_id=user_id,
            event_type='retired',
            description=description or '设备退役',
            operator=operator or 'system',
            event_metadata=json.dumps(metadata or {})
        )
        db.session.add(event)
        
        # 更新设备在线状态
        device = Device.query.get(device_id)
        if device:
            device.is_online = False
        
        db.session.commit()
        
        logger.info(f"Device {device_id} retired")
        return {'success': True, 'event': event.to_dict()}
    
    @staticmethod
    def decommission_device(device_id: int, user_id: int, operator: str = None,
                           description: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """报废设备"""
        current_status = DeviceLifecycleService.get_current_status(device_id)
        
        if not DeviceLifecycleService.can_transition(current_status, 'decommissioned'):
            return {'success': False, 'message': f'无法从 {current_status} 状态报废设备'}
        
        event = DeviceLifecycleEvent(
            device_id=device_id,
            user_id=user_id,
            event_type='decommissioned',
            description=description or '设备报废',
            operator=operator or 'system',
            event_metadata=json.dumps(metadata or {})
        )
        db.session.add(event)
        db.session.commit()
        
        logger.info(f"Device {device_id} decommissioned")
        return {'success': True, 'event': event.to_dict()}
    
    @staticmethod
    def get_lifecycle_history(device_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """获取设备生命周期历史"""
        events = DeviceLifecycleEvent.query.filter_by(
            device_id=device_id
        ).order_by(DeviceLifecycleEvent.created_at.desc()).limit(limit).all()
        
        return [e.to_dict() for e in events]
    
    @staticmethod
    def create_maintenance_record(device_id: int, user_id: int, 
                                 maintenance_type: str, title: str,
                                 description: str = None,
                                 scheduled_at: datetime = None,
                                 assigned_to: str = None,
                                 cost: float = 0.0) -> Dict[str, Any]:
        """创建维护记录"""
        device = Device.query.get(device_id)
        if not device:
            return {'success': False, 'message': '设备不存在'}
        
        record = DeviceMaintenanceRecord(
            device_id=device_id,
            user_id=user_id,
            maintenance_type=maintenance_type,
            status='scheduled',
            title=title,
            description=description,
            scheduled_at=scheduled_at,
            assigned_to=assigned_to,
            cost=cost
        )
        db.session.add(record)
        db.session.commit()
        
        logger.info(f"Maintenance record created for device {device_id}")
        return {'success': True, 'record': record.to_dict()}
    
    @staticmethod
    def update_maintenance_status(record_id: int, status: str, 
                                 performed_by: str = None,
                                 result: str = None,
                                 notes: str = None) -> Dict[str, Any]:
        """更新维护记录状态"""
        record = DeviceMaintenanceRecord.query.get(record_id)
        if not record:
            return {'success': False, 'message': '维护记录不存在'}
        
        record.status = status
        
        if status == 'in_progress' and not record.started_at:
            record.started_at = datetime.utcnow()
        elif status == 'completed':
            record.completed_at = datetime.utcnow()
            if performed_by:
                record.performed_by = performed_by
            if result:
                record.result = result
            if notes:
                record.notes = notes
        
        db.session.commit()
        
        logger.info(f"Maintenance record {record_id} status updated to {status}")
        return {'success': True, 'record': record.to_dict()}
    
    @staticmethod
    def get_maintenance_records(device_id: int = None, user_id: int = None,
                               status: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """获取维护记录"""
        query = DeviceMaintenanceRecord.query
        
        if device_id:
            query = query.filter_by(device_id=device_id)
        if user_id:
            query = query.filter_by(user_id=user_id)
        if status:
            query = query.filter_by(status=status)
        
        records = query.order_by(DeviceMaintenanceRecord.created_at.desc()).limit(limit).all()
        return [r.to_dict() for r in records]
    
    @staticmethod
    def get_lifecycle_statistics(user_id: int = None) -> Dict[str, Any]:
        """获取生命周期统计"""
        query = DeviceLifecycleEvent.query
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        events = query.all()
        
        stats = {
            'total_events': len(events),
            'by_type': {},
            'by_month': {}
        }
        
        for event in events:
            # 按类型统计
            event_type = event.event_type
            stats['by_type'][event_type] = stats['by_type'].get(event_type, 0) + 1
            
            # 按月份统计
            month_key = event.created_at.strftime('%Y-%m')
            stats['by_month'][month_key] = stats['by_month'].get(month_key, 0) + 1
        
        return stats
