"""
数据备份服务
Data Backup Service
"""
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from models.database import (
    db, Backup, BackupSchedule, User, Device, DataPoint,
    AlarmRecord, AlarmRule, DeviceGroup, AuditLog
)
from sqlalchemy import desc

logger = logging.getLogger(__name__)

# 备份目录
BACKUP_DIR = os.environ.get('BACKUP_DIR', '/tmp/iot_backups')


class BackupService:
    """备份服务"""
    
    @staticmethod
    def _ensure_backup_dir():
        """确保备份目录存在"""
        os.makedirs(BACKUP_DIR, exist_ok=True)
    
    @staticmethod
    def create_backup(
        user_id: int,
        name: str,
        backup_type: str = 'full',
        description: Optional[str] = None,
        parent_backup_id: Optional[int] = None,
    ) -> Backup:
        """创建备份"""
        BackupService._ensure_backup_dir()
        
        backup = Backup(
            user_id=user_id,
            name=name,
            backup_type=backup_type,
            description=description,
            parent_backup_id=parent_backup_id,
            status='running'
        )
        
        db.session.add(backup)
        db.session.commit()
        
        try:
            # 执行备份
            backup_data = BackupService._collect_backup_data(user_id, backup_type, parent_backup_id)
            
            # 生成备份文件
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"backup_{backup_type}_{timestamp}_{backup.id}.json"
            file_path = os.path.join(BACKUP_DIR, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            # 更新备份记录
            backup.file_path = file_path
            backup.file_size = os.path.getsize(file_path)
            backup.content_stats = json.dumps(backup_data.get('stats', {}))
            backup.status = 'completed'
            backup.completed_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"备份完成: {backup.id}, 文件: {file_path}")
            
        except Exception as e:
            backup.status = 'failed'
            backup.error_message = str(e)
            db.session.commit()
            logger.error(f"备份失败: {backup.id}, 错误: {e}")
            raise
        
        return backup
    
    @staticmethod
    def _collect_backup_data(user_id: int, backup_type: str, parent_backup_id: Optional[int]) -> Dict[str, Any]:
        """收集备份数据"""
        data = {
            'version': '1.0',
            'backup_type': backup_type,
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat(),
            'stats': {},
            'data': {}
        }
        
        # 全量备份
        if backup_type == 'full':
            # 设备数据
            devices = Device.query.filter_by(user_id=user_id).all()
            data['data']['devices'] = [d.to_dict() for d in devices]
            data['stats']['devices'] = len(devices)
            
            # 告警规则
            rules = AlarmRule.query.filter_by(user_id=user_id).all()
            data['data']['alarm_rules'] = [r.to_dict() for r in rules]
            data['stats']['alarm_rules'] = len(rules)
            
            # 设备分组
            groups = DeviceGroup.query.filter_by(user_id=user_id).all()
            data['data']['device_groups'] = [g.to_dict() for g in groups]
            data['stats']['device_groups'] = len(groups)
            
            # 最近7天的数据点 (通过 channel 关联设备)
            week_ago = datetime.utcnow() - timedelta(days=7)
            # 简化处理：只备份最近的数据点数量统计
            data_point_count = DataPoint.query.filter(
                DataPoint.timestamp >= week_ago
            ).count()
            data['stats']['recent_data_points'] = data_point_count
            
            # 告警记录 (通过 user_id 关联)
            alarms = AlarmRecord.query.filter_by(
                user_id=user_id
            ).order_by(desc(AlarmRecord.created_at)).limit(1000).all()
            data['data']['alarms'] = [a.to_dict() for a in alarms]
            data['stats']['alarms'] = len(alarms)
        
        # 增量备份 (基于父备份)
        elif backup_type == 'incremental' and parent_backup_id:
            parent = Backup.query.get(parent_backup_id)
            if parent and parent.completed_at:
                # 只备份父备份之后变更的数据
                since = parent.completed_at
                
                devices = Device.query.filter(
                    Device.user_id == user_id,
                    Device.updated_at >= since
                ).all()
                data['data']['devices'] = [d.to_dict() for d in devices]
                data['stats']['devices'] = len(devices)
                
                # 增量备份只统计变更数量
                data_point_count = DataPoint.query.filter(
                    DataPoint.timestamp >= since
                ).count()
                data['stats']['new_data_points'] = data_point_count
        
        return data
    
    @staticmethod
    def restore_backup(backup_id: int, user_id: int) -> Dict[str, Any]:
        """恢复备份"""
        backup = Backup.query.filter_by(id=backup_id, user_id=user_id).first()
        if not backup:
            raise ValueError(f"备份不存在: {backup_id}")
        
        if not backup.restorable:
            raise ValueError("该备份不可恢复")
        
        if backup.status != 'completed':
            raise ValueError("备份未完成，无法恢复")
        
        if not backup.file_path or not os.path.exists(backup.file_path):
            raise ValueError("备份文件不存在")
        
        # 读取备份数据
        with open(backup.file_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        restored = {
            'devices': 0,
            'alarm_rules': 0,
            'device_groups': 0,
            'device_data': 0,
            'alarms': 0
        }
        
        # 恢复设备分组
        for group_data in backup_data.get('data', {}).get('device_groups', []):
            try:
                group = DeviceGroup.query.filter_by(
                    user_id=user_id, name=group_data.get('name')
                ).first()
                if not group:
                    group = DeviceGroup(
                        user_id=user_id,
                        name=group_data.get('name'),
                        description=group_data.get('description')
                    )
                    db.session.add(group)
                    restored['device_groups'] += 1
            except Exception as e:
                logger.warning(f"恢复分组失败: {e}")
        
        # 恢复设备
        for device_data in backup_data.get('data', {}).get('devices', []):
            try:
                device = Device.query.filter_by(
                    user_id=user_id, name=device_data.get('name')
                ).first()
                if not device:
                    device = Device(
                        user_id=user_id,
                        name=device_data.get('name'),
                        device_type=device_data.get('device_type'),
                        location=device_data.get('location'),
                        status=device_data.get('status', 'offline')
                    )
                    db.session.add(device)
                    restored['devices'] += 1
            except Exception as e:
                logger.warning(f"恢复设备失败: {e}")
        
        # 恢复告警规则
        for rule_data in backup_data.get('data', {}).get('alarm_rules', []):
            try:
                rule = AlarmRule.query.filter_by(
                    user_id=user_id, name=rule_data.get('name')
                ).first()
                if not rule:
                    rule = AlarmRule(
                        user_id=user_id,
                        name=rule_data.get('name'),
                        description=rule_data.get('description'),
                        metric=rule_data.get('metric'),
                        condition=rule_data.get('condition'),
                        threshold=rule_data.get('threshold'),
                        severity=rule_data.get('severity', 'warning'),
                        enabled=rule_data.get('enabled', True)
                    )
                    db.session.add(rule)
                    restored['alarm_rules'] += 1
            except Exception as e:
                logger.warning(f"恢复告警规则失败: {e}")
        
        db.session.commit()
        
        logger.info(f"备份恢复完成: {backup.id}, 恢复统计: {restored}")
        
        return {
            'backup_id': backup_id,
            'restored': restored,
            'message': '备份恢复完成'
        }
    
    @staticmethod
    def delete_backup(backup_id: int, user_id: int) -> bool:
        """删除备份"""
        backup = Backup.query.filter_by(id=backup_id, user_id=user_id).first()
        if not backup:
            raise ValueError(f"备份不存在: {backup_id}")
        
        # 删除备份文件
        if backup.file_path and os.path.exists(backup.file_path):
            os.remove(backup.file_path)
        
        db.session.delete(backup)
        db.session.commit()
        
        logger.info(f"删除备份: {backup.id}")
        return True
    
    @staticmethod
    def get_backup(backup_id: int, user_id: int) -> Optional[Backup]:
        """获取备份详情"""
        return Backup.query.filter_by(id=backup_id, user_id=user_id).first()
    
    @staticmethod
    def list_backups(
        user_id: int,
        backup_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """获取备份列表"""
        query = Backup.query.filter_by(user_id=user_id)
        
        if backup_type:
            query = query.filter_by(backup_type=backup_type)
        
        if status:
            query = query.filter_by(status=status)
        
        query = query.order_by(desc(Backup.created_at))
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'backups': [b.to_dict() for b in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    
    @staticmethod
    def get_backup_statistics(user_id: int) -> Dict[str, Any]:
        """获取备份统计"""
        total_backups = Backup.query.filter_by(user_id=user_id).count()
        completed_backups = Backup.query.filter_by(user_id=user_id, status='completed').count()
        failed_backups = Backup.query.filter_by(user_id=user_id, status='failed').count()
        
        total_size = db.session.query(db.func.sum(Backup.file_size)).filter_by(
            user_id=user_id, status='completed'
        ).scalar() or 0
        
        latest_backup = Backup.query.filter_by(
            user_id=user_id, status='completed'
        ).order_by(desc(Backup.completed_at)).first()
        
        return {
            'total_backups': total_backups,
            'completed_backups': completed_backups,
            'failed_backups': failed_backups,
            'total_size': total_size,
            'total_size_human': Backup._format_size(total_size),
            'latest_backup': latest_backup.to_dict() if latest_backup else None
        }
    
    @staticmethod
    def cleanup_old_backups(user_id: int, retention_days: int = 30) -> int:
        """清理过期备份"""
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        old_backups = Backup.query.filter(
            Backup.user_id == user_id,
            Backup.created_at < cutoff_date
        ).all()
        
        deleted_count = 0
        for backup in old_backups:
            try:
                BackupService.delete_backup(backup.id, user_id)
                deleted_count += 1
            except Exception as e:
                logger.warning(f"清理备份失败: {backup.id}, 错误: {e}")
        
        logger.info(f"清理过期备份: 删除 {deleted_count} 个")
        return deleted_count


class BackupScheduleService:
    """备份定时任务服务"""
    
    @staticmethod
    def create_schedule(
        user_id: int,
        name: str,
        backup_type: str = 'full',
        schedule_hour: int = 2,
        schedule_day_of_week: Optional[int] = None,
        schedule_day_of_month: Optional[int] = None,
        retention_days: int = 30,
        max_backups: int = 10,
    ) -> BackupSchedule:
        """创建备份定时任务"""
        schedule = BackupSchedule(
            user_id=user_id,
            name=name,
            backup_type=backup_type,
            schedule_hour=schedule_hour,
            schedule_day_of_week=schedule_day_of_week,
            schedule_day_of_month=schedule_day_of_month,
            retention_days=retention_days,
            max_backups=max_backups,
            enabled=True
        )
        
        db.session.add(schedule)
        db.session.commit()
        
        logger.info(f"创建备份定时任务: {schedule.id}, name: {name}")
        return schedule
    
    @staticmethod
    def update_schedule(
        schedule_id: int,
        user_id: int,
        **kwargs
    ) -> BackupSchedule:
        """更新备份定时任务"""
        schedule = BackupSchedule.query.filter_by(id=schedule_id, user_id=user_id).first()
        if not schedule:
            raise ValueError(f"定时任务不存在: {schedule_id}")
        
        for key, value in kwargs.items():
            if hasattr(schedule, key) and value is not None:
                setattr(schedule, key, value)
        
        db.session.commit()
        
        logger.info(f"更新备份定时任务: {schedule.id}")
        return schedule
    
    @staticmethod
    def delete_schedule(schedule_id: int, user_id: int) -> bool:
        """删除备份定时任务"""
        schedule = BackupSchedule.query.filter_by(id=schedule_id, user_id=user_id).first()
        if not schedule:
            raise ValueError(f"定时任务不存在: {schedule_id}")
        
        db.session.delete(schedule)
        db.session.commit()
        
        logger.info(f"删除备份定时任务: {schedule.id}")
        return True
    
    @staticmethod
    def toggle_schedule(schedule_id: int, user_id: int, enabled: bool) -> BackupSchedule:
        """启用/禁用备份定时任务"""
        schedule = BackupSchedule.query.filter_by(id=schedule_id, user_id=user_id).first()
        if not schedule:
            raise ValueError(f"定时任务不存在: {schedule_id}")
        
        schedule.enabled = enabled
        db.session.commit()
        
        logger.info(f"备份定时任务状态变更: {schedule.id}, enabled: {enabled}")
        return schedule
    
    @staticmethod
    def list_schedules(user_id: int) -> List[BackupSchedule]:
        """获取备份定时任务列表"""
        return BackupSchedule.query.filter_by(user_id=user_id).order_by(
            desc(BackupSchedule.created_at)
        ).all()
