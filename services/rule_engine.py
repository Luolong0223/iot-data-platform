"""
规则引擎服务 (Rule Engine Service)
支持条件触发自动化动作：告警、命令、通知、Webhook
"""
import json
import logging
import requests as http_requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from models.database import db, Rule, RuleAction, RuleExecutionLog, Device, DataPoint
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class RuleEngineService:
    """规则引擎服务类"""

    @staticmethod
    def create_rule(user_id: int, name: str, conditions: Dict[str, Any], 
                   actions: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """创建规则"""
        try:
            rule = Rule(
                user_id=user_id,
                name=name,
                description=kwargs.get('description'),
                conditions=json.dumps(conditions, ensure_ascii=False),
                is_enabled=kwargs.get('is_enabled', True),
                priority=kwargs.get('priority', 5),
                cooldown_seconds=kwargs.get('cooldown_seconds', 300)
            )
            db.session.add(rule)
            db.session.flush()  # 获取 rule.id
            
            # 创建动作
            for idx, action in enumerate(actions):
                rule_action = RuleAction(
                    rule_id=rule.id,
                    action_type=action['type'],
                    config=json.dumps(action.get('config', {}), ensure_ascii=False),
                    order=idx
                )
                db.session.add(rule_action)
            
            db.session.commit()
            logger.info(f"Created rule: {name} (id={rule.id})")
            return {'success': True, 'rule': rule.to_dict()}
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to create rule: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def update_rule(rule_id: int, user_id: int, **kwargs) -> Dict[str, Any]:
        """更新规则"""
        try:
            rule = Rule.query.filter_by(id=rule_id, user_id=user_id).first()
            if not rule:
                return {'success': False, 'error': '规则不存在'}
            
            if 'name' in kwargs:
                rule.name = kwargs['name']
            if 'description' in kwargs:
                rule.description = kwargs['description']
            if 'conditions' in kwargs:
                rule.conditions = json.dumps(kwargs['conditions'], ensure_ascii=False)
            if 'is_enabled' in kwargs:
                rule.is_enabled = kwargs['is_enabled']
            if 'priority' in kwargs:
                rule.priority = kwargs['priority']
            if 'cooldown_seconds' in kwargs:
                rule.cooldown_seconds = kwargs['cooldown_seconds']
            
            # 更新动作
            if 'actions' in kwargs:
                # 删除旧动作
                RuleAction.query.filter_by(rule_id=rule_id).delete()
                # 创建新动作
                for idx, action in enumerate(kwargs['actions']):
                    rule_action = RuleAction(
                        rule_id=rule_id,
                        action_type=action['type'],
                        config=json.dumps(action.get('config', {}), ensure_ascii=False),
                        order=idx
                    )
                    db.session.add(rule_action)
            
            db.session.commit()
            logger.info(f"Updated rule: {rule.name} (id={rule.id})")
            return {'success': True, 'rule': rule.to_dict()}
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to update rule: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def delete_rule(rule_id: int, user_id: int) -> Dict[str, Any]:
        """删除规则"""
        try:
            rule = Rule.query.filter_by(id=rule_id, user_id=user_id).first()
            if not rule:
                return {'success': False, 'error': '规则不存在'}
            
            db.session.delete(rule)
            db.session.commit()
            logger.info(f"Deleted rule: {rule.name} (id={rule.id})")
            return {'success': True, 'message': '规则已删除'}
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to delete rule: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_rules(user_id: int, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """获取用户的所有规则"""
        query = Rule.query.filter_by(user_id=user_id)
        if enabled_only:
            query = query.filter_by(is_enabled=True)
        rules = query.order_by(Rule.priority.desc(), Rule.created_at.desc()).all()
        return [r.to_dict() for r in rules]

    @staticmethod
    def get_rule(rule_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """获取单个规则"""
        rule = Rule.query.filter_by(id=rule_id, user_id=user_id).first()
        return rule.to_dict() if rule else None

    @staticmethod
    def evaluate_condition(condition: Dict[str, Any], device_id: int) -> bool:
        """评估单个条件是否满足"""
        try:
            metric = condition.get('metric')
            operator = condition.get('operator')
            threshold = condition.get('value')
            
            # 获取设备的所有通道
            from models.database import SlaveChannel
            channels = SlaveChannel.query.filter_by(device_id=device_id).all()
            if not channels:
                return False
            
            channel_ids = [c.id for c in channels]
            
            # 获取最新数据点
            data_point = DataPoint.query.filter(
                DataPoint.channel_id.in_(channel_ids),
                DataPoint.name == metric
            ).order_by(DataPoint.timestamp.desc()).first()
            
            if not data_point:
                return False
            
            value = float(data_point.value)
            threshold = float(threshold)
            
            if operator == '>':
                return value > threshold
            elif operator == '>=':
                return value >= threshold
            elif operator == '<':
                return value < threshold
            elif operator == '<=':
                return value <= threshold
            elif operator == '==':
                return value == threshold
            elif operator == '!=':
                return value != threshold
            else:
                return False
        except Exception as e:
            logger.error(f"Failed to evaluate condition: {e}")
            return False

    @staticmethod
    def check_cooldown(rule: Rule) -> bool:
        """检查规则是否在冷却期内"""
        if not rule.last_triggered_at:
            return False
        
        cooldown_end = rule.last_triggered_at + timedelta(seconds=rule.cooldown_seconds)
        return datetime.utcnow() < cooldown_end

    @staticmethod
    def execute_action(action: RuleAction, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个动作"""
        try:
            config = json.loads(action.config) if action.config else {}
            action_type = action.action_type
            
            if action_type == 'alarm':
                # 创建告警
                from models.database import AlarmRecord
                alarm = AlarmRecord(
                    device_id=context.get('device_id'),
                    alarm_type=config.get('severity', 'warning'),
                    message=config.get('message', '规则触发告警'),
                    value=context.get('value'),
                    threshold=config.get('threshold'),
                    status='active'
                )
                db.session.add(alarm)
                db.session.commit()
                return {'success': True, 'type': 'alarm', 'alarm_id': alarm.id}
            
            elif action_type == 'command':
                # 发送命令（这里简化为记录日志）
                logger.info(f"Command sent to device {config.get('device_id')}: {config.get('command')}")
                return {'success': True, 'type': 'command', 'command': config.get('command')}
            
            elif action_type == 'notification':
                # 发送通知（这里简化为记录日志）
                logger.info(f"Notification sent: {config.get('message')}")
                return {'success': True, 'type': 'notification', 'channel': config.get('channel')}
            
            elif action_type == 'webhook':
                # 调用 Webhook
                url = config.get('url')
                method = config.get('method', 'POST')
                headers = config.get('headers', {})
                payload = config.get('payload', context)
                
                response = http_requests.request(
                    method=method,
                    url=url,
                    json=payload,
                    headers=headers,
                    timeout=10
                )
                return {
                    'success': response.status_code < 400,
                    'type': 'webhook',
                    'status_code': response.status_code
                }
            
            else:
                return {'success': False, 'error': f'Unknown action type: {action_type}'}
        except Exception as e:
            logger.error(f"Failed to execute action: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def trigger_rule(rule_id: int, device_id: int, context: Dict[str, Any]) -> Dict[str, Any]:
        """触发规则执行"""
        try:
            rule = Rule.query.get(rule_id)
            if not rule or not rule.is_enabled:
                return {'success': False, 'error': '规则不存在或未启用'}
            
            # 检查冷却期
            if RuleEngineService.check_cooldown(rule):
                # 记录跳过
                log = RuleExecutionLog(
                    rule_id=rule_id,
                    device_id=device_id,
                    trigger_data=json.dumps(context, ensure_ascii=False),
                    status='skipped',
                    error_message='冷却期内，跳过执行'
                )
                db.session.add(log)
                db.session.commit()
                return {'success': False, 'error': '冷却期内，跳过执行'}
            
            # 执行所有动作
            action_results = []
            all_success = True
            for action in rule.actions.order_by(RuleAction.order):
                result = RuleEngineService.execute_action(action, context)
                action_results.append(result)
                if not result.get('success'):
                    all_success = False
            
            # 更新规则状态
            rule.trigger_count += 1
            rule.last_triggered_at = datetime.utcnow()
            
            # 记录执行日志
            log = RuleExecutionLog(
                rule_id=rule_id,
                device_id=device_id,
                trigger_data=json.dumps(context, ensure_ascii=False),
                status='success' if all_success else 'failed',
                action_results=json.dumps(action_results, ensure_ascii=False)
            )
            db.session.add(log)
            db.session.commit()
            
            logger.info(f"Rule {rule.name} triggered, actions: {len(action_results)}")
            return {
                'success': True,
                'rule_id': rule_id,
                'action_results': action_results
            }
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to trigger rule: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def evaluate_and_trigger(device_id: int, data_point_name: str, value: float) -> List[Dict[str, Any]]:
        """评估所有相关规则并触发"""
        results = []
        
        # 获取设备所属用户
        device = Device.query.get(device_id)
        if not device:
            return results
        
        # 获取用户的所有启用规则
        rules = Rule.query.filter_by(user_id=device.user_id, is_enabled=True)\
            .order_by(Rule.priority.desc()).all()
        
        for rule in rules:
            try:
                conditions = json.loads(rule.conditions) if rule.conditions else {}
                
                # 检查条件是否匹配
                if conditions.get('device_id') and conditions.get('device_id') != device_id:
                    continue
                if conditions.get('metric') and conditions.get('metric') != data_point_name:
                    continue
                
                # 评估条件
                if RuleEngineService.evaluate_condition(conditions, device_id):
                    context = {
                        'device_id': device_id,
                        'device_name': device.name,
                        'metric': data_point_name,
                        'value': value,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    result = RuleEngineService.trigger_rule(rule.id, device_id, context)
                    results.append({
                        'rule_id': rule.id,
                        'rule_name': rule.name,
                        'result': result
                    })
            except Exception as e:
                logger.error(f"Failed to evaluate rule {rule.id}: {e}")
        
        return results

    @staticmethod
    def get_execution_logs(rule_id: int, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """获取规则执行日志"""
        rule = Rule.query.filter_by(id=rule_id, user_id=user_id).first()
        if not rule:
            return []
        
        logs = RuleExecutionLog.query.filter_by(rule_id=rule_id)\
            .order_by(RuleExecutionLog.executed_at.desc())\
            .limit(limit)\
            .all()
        return [log.to_dict() for log in logs]

    @staticmethod
    def test_rule(rule_id: int, user_id: int, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """测试规则（不实际执行动作，只返回预期结果）"""
        rule = Rule.query.filter_by(id=rule_id, user_id=user_id).first()
        if not rule:
            return {'success': False, 'error': '规则不存在'}
        
        conditions = json.loads(rule.conditions) if rule.conditions else {}
        device_id = test_data.get('device_id', conditions.get('device_id'))
        
        # 评估条件
        condition_met = RuleEngineService.evaluate_condition(conditions, device_id) if device_id else False
        
        # 模拟执行动作
        action_results = []
        for action in rule.actions.order_by(RuleAction.order):
            config = json.loads(action.config) if action.config else {}
            action_results.append({
                'type': action.action_type,
                'config': config,
                'would_execute': condition_met
            })
        
        return {
            'success': True,
            'condition_met': condition_met,
            'action_results': action_results,
            'message': '条件满足，将执行以上动作' if condition_met else '条件不满足，不会执行动作'
        }
