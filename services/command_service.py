"""
命令中心服务
Command Center Service
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from models.database import db, DeviceCommand, CommandTemplate, Device
from sqlalchemy import desc

logger = logging.getLogger(__name__)


class CommandService:
    """命令服务"""
    
    @staticmethod
    def create_command(
        user_id: int,
        device_id: int,
        command: str,
        payload: Optional[Dict] = None,
    ) -> DeviceCommand:
        """创建设备命令"""
        # 验证设备存在
        device = Device.query.filter_by(id=device_id, user_id=user_id).first()
        if not device:
            raise ValueError(f"设备不存在: {device_id}")
        
        cmd = DeviceCommand(
            device_id=device_id,
            command=command,
            payload=json.dumps(payload) if payload else None,
            status='pending',
            created_by=user_id
        )
        
        db.session.add(cmd)
        db.session.commit()
        
        logger.info(f"创建命令: {cmd.id}, 设备: {device_id}, 类型: {command}")
        return cmd
    
    @staticmethod
    def send_command(command_id: int, user_id: int) -> DeviceCommand:
        """发送命令到设备"""
        cmd = DeviceCommand.query.filter_by(id=command_id, created_by=user_id).first()
        if not cmd:
            raise ValueError(f"命令不存在: {command_id}")
        
        if cmd.status not in ['pending', 'failed']:
            raise ValueError(f"命令状态不允许发送: {cmd.status}")
        
        # 更新状态为已发送
        cmd.status = 'sent'
        cmd.sent_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"发送命令: {cmd.id} 到设备: {cmd.device_id}")
        
        # TODO: 实际发送命令到设备（通过MQTT、HTTP等）
        # 这里模拟发送成功
        
        return cmd
    
    @staticmethod
    def update_command_status(
        command_id: int,
        user_id: int,
        status: str,
        result: Optional[str] = None,
    ) -> DeviceCommand:
        """更新命令状态"""
        cmd = DeviceCommand.query.filter_by(id=command_id, created_by=user_id).first()
        if not cmd:
            raise ValueError(f"命令不存在: {command_id}")
        
        cmd.status = status
        
        if status in ['ack', 'failed']:
            cmd.ack_at = datetime.utcnow()
        
        if result:
            cmd.result = result
        
        db.session.commit()
        
        logger.info(f"更新命令状态: {cmd.id}, 状态: {status}")
        return cmd
    
    @staticmethod
    def cancel_command(command_id: int, user_id: int) -> DeviceCommand:
        """取消命令"""
        cmd = DeviceCommand.query.filter_by(id=command_id, created_by=user_id).first()
        if not cmd:
            raise ValueError(f"命令不存在: {command_id}")
        
        if cmd.status in ['ack', 'failed']:
            raise ValueError(f"命令已完成，无法取消: {cmd.status}")
        
        cmd.status = 'failed'
        cmd.result = 'cancelled'
        cmd.ack_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"取消命令: {cmd.id}")
        return cmd
    
    @staticmethod
    def retry_command(command_id: int, user_id: int) -> DeviceCommand:
        """重试命令"""
        cmd = DeviceCommand.query.filter_by(id=command_id, created_by=user_id).first()
        if not cmd:
            raise ValueError(f"命令不存在: {command_id}")
        
        if cmd.status != 'failed':
            raise ValueError(f"只能重试失败的命令: {cmd.status}")
        
        # 重置状态
        cmd.status = 'pending'
        cmd.result = None
        cmd.sent_at = None
        cmd.ack_at = None
        
        db.session.commit()
        
        logger.info(f"重试命令: {cmd.id}")
        return cmd
    
    @staticmethod
    def get_command(command_id: int, user_id: int) -> Optional[DeviceCommand]:
        """获取命令详情"""
        return DeviceCommand.query.filter_by(id=command_id, created_by=user_id).first()
    
    @staticmethod
    def list_commands(
        user_id: int,
        device_id: Optional[int] = None,
        status: Optional[str] = None,
        command: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """获取命令列表"""
        query = DeviceCommand.query.filter_by(created_by=user_id)
        
        if device_id:
            query = query.filter_by(device_id=device_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if command:
            query = query.filter_by(command=command)
        
        query = query.order_by(desc(DeviceCommand.created_at))
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'commands': [cmd.to_dict() for cmd in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    
    @staticmethod
    def get_pending_commands(device_id: int) -> List[DeviceCommand]:
        """获取设备的待发送命令"""
        return DeviceCommand.query.filter_by(
            device_id=device_id,
            status='pending'
        ).order_by(DeviceCommand.created_at).all()
    
    @staticmethod
    def get_command_statistics(user_id: int, days: int = 7) -> Dict[str, Any]:
        """获取命令统计"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        commands = DeviceCommand.query.filter(
            DeviceCommand.created_by == user_id,
            DeviceCommand.created_at >= start_date
        ).all()
        
        total = len(commands)
        by_status = {}
        by_command = {}
        success_count = 0
        failed_count = 0
        
        for cmd in commands:
            # 按状态统计
            by_status[cmd.status] = by_status.get(cmd.status, 0) + 1
            
            # 按命令类型统计
            by_command[cmd.command] = by_command.get(cmd.command, 0) + 1
            
            # 成功/失败计数
            if cmd.status == 'ack':
                success_count += 1
            elif cmd.status == 'failed':
                failed_count += 1
        
        success_rate = (success_count / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'by_status': by_status,
            'by_command': by_command,
            'success_count': success_count,
            'failed_count': failed_count,
            'success_rate': round(success_rate, 2),
            'days': days
        }
    
    @staticmethod
    def cleanup_old_commands(user_id: int, days: int = 30) -> int:
        """清理旧命令"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted = DeviceCommand.query.filter(
            DeviceCommand.created_by == user_id,
            DeviceCommand.created_at < cutoff_date,
            DeviceCommand.status.in_(['ack', 'failed'])
        ).delete(synchronize_session=False)
        
        db.session.commit()
        
        logger.info(f"清理旧命令: {deleted} 条, 用户: {user_id}, 天数: {days}")
        return deleted


class CommandTemplateService:
    """命令模板服务"""
    
    @staticmethod
    def create_template(
        user_id: int,
        name: str,
        command_type: str,
        description: Optional[str] = None,
        default_parameters: Optional[Dict] = None,
        default_timeout: int = 30,
        default_priority: int = 5
    ) -> CommandTemplate:
        """创建命令模板"""
        template = CommandTemplate(
            user_id=user_id,
            name=name,
            command_type=command_type,
            description=description,
            default_parameters=json.dumps(default_parameters) if default_parameters else None,
            default_timeout=default_timeout,
            default_priority=default_priority
        )
        
        db.session.add(template)
        db.session.commit()
        
        logger.info(f"创建命令模板: {template.id}, 名称: {name}")
        return template
    
    @staticmethod
    def update_template(
        template_id: int,
        user_id: int,
        **kwargs
    ) -> CommandTemplate:
        """更新命令模板"""
        template = CommandTemplate.query.filter_by(id=template_id, user_id=user_id).first()
        if not template:
            raise ValueError(f"模板不存在: {template_id}")
        
        for key, value in kwargs.items():
            if hasattr(template, key):
                if key == 'default_parameters' and value:
                    value = json.dumps(value)
                setattr(template, key, value)
        
        db.session.commit()
        
        logger.info(f"更新命令模板: {template.id}")
        return template
    
    @staticmethod
    def delete_template(template_id: int, user_id: int) -> bool:
        """删除命令模板"""
        template = CommandTemplate.query.filter_by(id=template_id, user_id=user_id).first()
        if not template:
            raise ValueError(f"模板不存在: {template_id}")
        
        db.session.delete(template)
        db.session.commit()
        
        logger.info(f"删除命令模板: {template.id}")
        return True
    
    @staticmethod
    def get_template(template_id: int, user_id: int) -> Optional[CommandTemplate]:
        """获取模板详情"""
        return CommandTemplate.query.filter_by(id=template_id, user_id=user_id).first()
    
    @staticmethod
    def list_templates(
        user_id: int,
        command_type: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """获取模板列表"""
        query = CommandTemplate.query.filter_by(user_id=user_id)
        
        if command_type:
            query = query.filter_by(command_type=command_type)
        
        query = query.order_by(desc(CommandTemplate.created_at))
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'templates': [tmpl.to_dict() for tmpl in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    
    @staticmethod
    def create_command_from_template(
        template_id: int,
        user_id: int,
        device_id: int,
        parameters: Optional[Dict] = None
    ) -> DeviceCommand:
        """从模板创建命令"""
        template = CommandTemplate.query.filter_by(id=template_id, user_id=user_id).first()
        if not template:
            raise ValueError(f"模板不存在: {template_id}")
        
        # 合并参数
        final_params = {}
        if template.default_parameters:
            final_params.update(json.loads(template.default_parameters))
        if parameters:
            final_params.update(parameters)
        
        return CommandService.create_command(
            user_id=user_id,
            device_id=device_id,
            command=template.command_type,
            payload=final_params if final_params else None,
        )
