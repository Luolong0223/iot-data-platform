"""
多协议适配器服务
支持 MQTT、CoAP、Modbus、HTTP 等协议的设备接入与数据解析
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from models.database import db, ProtocolAdapter, ProtocolMessage, Device, DataPoint, SlaveChannel
from services.device_shadow import DeviceShadowService

logger = logging.getLogger(__name__)


class ProtocolAdapterService:
    """协议适配器服务"""
    
    SUPPORTED_PROTOCOLS = ['mqtt', 'coap', 'modbus', 'http']
    
    @staticmethod
    def create_adapter(user_id: int, name: str, protocol_type: str, 
                      connection_config: Dict, parse_rules: Optional[Dict] = None) -> ProtocolAdapter:
        """创建协议适配器"""
        if protocol_type not in ProtocolAdapterService.SUPPORTED_PROTOCOLS:
            raise ValueError(f"不支持的协议类型: {protocol_type}")
        
        adapter = ProtocolAdapter(
            user_id=user_id,
            name=name,
            protocol=protocol_type,
            config=json.dumps(connection_config),
            codec=json.dumps(parse_rules) if parse_rules else None,
            enabled=True
        )
        db.session.add(adapter)
        db.session.commit()
        
        logger.info(f"创建协议适配器: {name} ({protocol_type})")
        return adapter
    
    @staticmethod
    def update_adapter(adapter_id: int, user_id: int, **kwargs) -> ProtocolAdapter:
        """更新协议适配器"""
        adapter = ProtocolAdapter.query.filter_by(id=adapter_id, user_id=user_id).first()
        if not adapter:
            raise ValueError("适配器不存在")
        
        if 'connection_config' in kwargs:
            adapter.config = json.dumps(kwargs['connection_config'])
        if 'parse_rules' in kwargs:
            adapter.codec = json.dumps(kwargs['parse_rules'])
        if 'name' in kwargs:
            adapter.name = kwargs['name']
        if 'is_enabled' in kwargs:
            adapter.enabled = kwargs['is_enabled']
        
        adapter.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"更新协议适配器: {adapter.name}")
        return adapter
    
    @staticmethod
    def test_connection(adapter_id: int, user_id: int) -> Dict[str, Any]:
        """测试协议连接"""
        adapter = ProtocolAdapter.query.filter_by(id=adapter_id, user_id=user_id).first()
        if not adapter:
            return {'success': False, 'message': '适配器不存在'}
        
        config = json.loads(adapter.config)
        
        try:
            if adapter.protocol == 'mqtt':
                return ProtocolAdapterService._test_mqtt(config)
            elif adapter.protocol == 'coap':
                return ProtocolAdapterService._test_coap(config)
            elif adapter.protocol == 'modbus':
                return ProtocolAdapterService._test_modbus(config)
            elif adapter.protocol == 'http':
                return ProtocolAdapterService._test_http(config)
            else:
                return {'success': False, 'message': f'不支持的协议: {adapter.protocol}'}
        except Exception as e:
            logger.error(f"测试连接失败: {e}")
            adapter.last_status = 'error'
            adapter.last_run_at = datetime.utcnow()
            db.session.commit()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def _test_mqtt(config: Dict) -> Dict[str, Any]:
        """测试 MQTT 连接"""
        try:
            import paho.mqtt.client as mqtt
            
            broker = config.get('broker', 'localhost')
            port = config.get('port', 1883)
            username = config.get('username')
            password = config.get('password')
            
            client = mqtt.Client()
            if username:
                client.username_pw_set(username, password)
            
            client.connect(broker, port, timeout=5)
            client.disconnect()
            
            return {'success': True, 'message': f'MQTT 连接成功: {broker}:{port}'}
        except ImportError:
            return {'success': True, 'message': 'MQTT 配置已保存（paho-mqtt 未安装，跳过实际连接测试）'}
        except Exception as e:
            return {'success': False, 'message': f'MQTT 连接失败: {str(e)}'}
    
    @staticmethod
    def _test_coap(config: Dict) -> Dict[str, Any]:
        """测试 CoAP 连接"""
        # CoAP 是无连接协议，这里只验证配置
        host = config.get('host', 'localhost')
        port = config.get('port', 5683)
        return {'success': True, 'message': f'CoAP 配置已验证: {host}:{port}'}
    
    @staticmethod
    def _test_modbus(config: Dict) -> Dict[str, Any]:
        """测试 Modbus 连接"""
        try:
            from pymodbus.client import ModbusTcpClient
            
            host = config.get('host', 'localhost')
            port = config.get('port', 502)
            
            client = ModbusTcpClient(host, port=port, timeout=5)
            connected = client.connect()
            client.close()
            
            if connected:
                return {'success': True, 'message': f'Modbus 连接成功: {host}:{port}'}
            else:
                return {'success': False, 'message': f'Modbus 连接失败: {host}:{port}'}
        except ImportError:
            return {'success': True, 'message': 'Modbus 配置已验证（pymodbus 未安装，跳过实际连接测试）'}
        except Exception as e:
            return {'success': False, 'message': f'Modbus 连接失败: {str(e)}'}
    
    @staticmethod
    def _test_http(config: Dict) -> Dict[str, Any]:
        """测试 HTTP 连接"""
        import requests
        
        url = config.get('url', 'http://localhost')
        method = config.get('method', 'GET')
        
        try:
            if method == 'GET':
                resp = requests.get(url, timeout=5)
            elif method == 'POST':
                resp = requests.post(url, json={}, timeout=5)
            else:
                return {'success': False, 'message': f'不支持的 HTTP 方法: {method}'}
            
            if resp.status_code < 400:
                return {'success': True, 'message': f'HTTP 连接成功: {url} (状态码: {resp.status_code})'}
            else:
                return {'success': False, 'message': f'HTTP 请求失败: 状态码 {resp.status_code}'}
        except Exception as e:
            return {'success': False, 'message': f'HTTP 连接失败: {str(e)}'}
    
    @staticmethod
    def process_inbound_message(adapter_id: int, topic: str, payload: bytes, qos: int = 0) -> Dict[str, Any]:
        """处理入站消息（设备→平台）"""
        adapter = ProtocolAdapter.query.get(adapter_id)
        if not adapter or not adapter.is_enabled:
            return {'success': False, 'message': '适配器未启用'}
        
        try:
            # 解析原始消息
            raw_payload = payload.decode('utf-8') if isinstance(payload, bytes) else payload
            
            # 根据解析规则处理数据
            parse_rules = json.loads(adapter.parse_rules) if adapter.parse_rules else {}
            parsed_data = ProtocolAdapterService._parse_message(raw_payload, parse_rules)
            
            # 记录消息
            message = ProtocolMessage(
                adapter_id=adapter_id,
                direction='inbound',
                raw_payload=json.dumps({'data': raw_payload}),
                parsed_data=json.dumps(parsed_data),
                status='success',
                topic=topic,
                qos=qos
            )
            
            # 更新统计
            adapter.message_count += 1
            adapter.last_run_at = datetime.utcnow()
            adapter.last_status = 'success'
            
            # 如果解析出设备数据，保存到 DataPoint
            if 'device_id' in parsed_data and 'data_points' in parsed_data:
                device_id = parsed_data['device_id']
                message.device_id = device_id
                
                for dp in parsed_data['data_points']:
                    ProtocolAdapterService._save_data_point(device_id, dp)
            
            db.session.add(message)
            db.session.commit()
            
            logger.info(f"处理入站消息: adapter={adapter.name}, topic={topic}")
            return {'success': True, 'message_id': message.id, 'parsed_data': parsed_data}
            
        except Exception as e:
            logger.error(f"处理入站消息失败: {e}")
            adapter.error_count += 1
            adapter.last_status = 'error'
            
            # 记录错误消息
            message = ProtocolMessage(
                adapter_id=adapter_id,
                direction='inbound',
                raw_payload=json.dumps({'data': payload.decode('utf-8', errors='ignore') if isinstance(payload, bytes) else payload}),
                status='failed',
                error_message=str(e),
                topic=topic,
                qos=qos
            )
            db.session.add(message)
            db.session.commit()
            
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def send_outbound_message(adapter_id: int, device_id: int, command: Dict[str, Any]) -> Dict[str, Any]:
        """发送出站消息（平台→设备）"""
        adapter = ProtocolAdapter.query.get(adapter_id)
        if not adapter or not adapter.is_enabled:
            return {'success': False, 'message': '适配器未启用'}
        
        config = json.loads(adapter.connection_config)
        
        try:
            # 根据协议类型发送消息
            if adapter.protocol_type == 'mqtt':
                result = ProtocolAdapterService._send_mqtt(config, device_id, command)
            elif adapter.protocol_type == 'coap':
                result = ProtocolAdapterService._send_coap(config, device_id, command)
            elif adapter.protocol_type == 'modbus':
                result = ProtocolAdapterService._send_modbus(config, device_id, command)
            elif adapter.protocol_type == 'http':
                result = ProtocolAdapterService._send_http(config, device_id, command)
            else:
                return {'success': False, 'message': f'不支持的协议: {adapter.protocol_type}'}
            
            # 记录消息
            message = ProtocolMessage(
                adapter_id=adapter_id,
                device_id=device_id,
                direction='outbound',
                raw_payload=json.dumps(command),
                status='success' if result.get('success') else 'failed',
                error_message=result.get('message'),
                topic=result.get('topic')
            )
            
            adapter.message_count += 1
            adapter.last_run_at = datetime.utcnow()
            adapter.last_status = 'success' if result.get('success') else 'error'
            db.session.add(message)
            db.session.commit()
            
            return result
            
        except Exception as e:
            logger.error(f"发送出站消息失败: {e}")
            adapter.error_count += 1
            adapter.last_status = 'error'
            
            message = ProtocolMessage(
                adapter_id=adapter_id,
                device_id=device_id,
                direction='outbound',
                raw_payload=json.dumps(command),
                status='failed',
                error_message=str(e)
            )
            db.session.add(message)
            db.session.commit()
            
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def _parse_message(raw_payload: str, parse_rules: Dict) -> Dict[str, Any]:
        """根据解析规则解析消息"""
        payload_format = parse_rules.get('payload_format', 'json')
        
        if payload_format == 'json':
            data = json.loads(raw_payload)
        elif payload_format == 'text':
            data = {'raw': raw_payload}
        else:
            data = {'raw': raw_payload}
        
        # 应用字段映射
        mappings = parse_rules.get('mappings', [])
        result = {'data_points': []}
        
        for mapping in mappings:
            source_field = mapping.get('source')
            target_field = mapping.get('target', source_field)
            unit = mapping.get('unit', '')
            
            if source_field in data:
                result['data_points'].append({
                    'name': target_field,
                    'value': data[source_field],
                    'unit': unit
                })
        
        # 如果没有映射规则，直接使用原始数据
        if not mappings and isinstance(data, dict):
            for key, value in data.items():
                if key not in ['device_id', 'timestamp']:
                    result['data_points'].append({
                        'name': key,
                        'value': value
                    })
        
        # 提取设备 ID
        if 'device_id' in data:
            result['device_id'] = data['device_id']
        
        return result
    
    @staticmethod
    def _save_data_point(device_id: int, data_point: Dict):
        """保存数据点到数据库"""
        device = Device.query.get(device_id)
        if not device:
            return
        
        # 查找或创建通道
        channel = SlaveChannel.query.filter_by(device_id=device_id, name='protocol_data').first()
        if not channel:
            channel = SlaveChannel(
                device_id=device_id,
                name='protocol_data',
                channel_type='modbus',
                is_enabled=True
            )
            db.session.add(channel)
            db.session.flush()
        
        # 创建数据点
        dp = DataPoint(
            channel_id=channel.id,
            name=data_point.get('name', 'unknown'),
            value=float(data_point.get('value', 0)),
            unit=data_point.get('unit', ''),
            timestamp=datetime.utcnow()
        )
        db.session.add(dp)
    
    @staticmethod
    def _send_mqtt(config: Dict, device_id: int, command: Dict) -> Dict[str, Any]:
        """发送 MQTT 消息"""
        try:
            import paho.mqtt.client as mqtt
            
            broker = config.get('broker', 'localhost')
            port = config.get('port', 1883)
            topic_prefix = config.get('topic_prefix', 'iot/')
            topic = f"{topic_prefix}device/{device_id}/command"
            
            client = mqtt.Client()
            username = config.get('username')
            password = config.get('password')
            if username:
                client.username_pw_set(username, password)
            
            client.connect(broker, port, timeout=5)
            client.publish(topic, json.dumps(command), qos=1)
            client.disconnect()
            
            return {'success': True, 'message': 'MQTT 消息已发送', 'topic': topic}
        except ImportError:
            return {'success': True, 'message': 'MQTT 消息已记录（paho-mqtt 未安装）', 'topic': f'device/{device_id}/command'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def _send_coap(config: Dict, device_id: int, command: Dict) -> Dict[str, Any]:
        """发送 CoAP 消息"""
        # CoAP 实现（简化版）
        host = config.get('host', 'localhost')
        port = config.get('port', 5683)
        uri = f"coap://{host}:{port}/device/{device_id}/command"
        
        return {'success': True, 'message': f'CoAP 消息已记录: {uri}', 'topic': uri}
    
    @staticmethod
    def _send_modbus(config: Dict, device_id: int, command: Dict) -> Dict[str, Any]:
        """发送 Modbus 命令"""
        try:
            from pymodbus.client import ModbusTcpClient
            
            host = config.get('host', 'localhost')
            port = config.get('port', 502)
            slave_id = config.get('slave_id', 1)
            
            client = ModbusTcpClient(host, port=port, timeout=5)
            connected = client.connect()
            
            if not connected:
                return {'success': False, 'message': 'Modbus 连接失败'}
            
            # 根据命令类型执行操作
            cmd_type = command.get('type', 'read')
            
            if cmd_type == 'read_coil':
                address = command.get('address', 0)
                count = command.get('count', 1)
                result = client.read_coils(address, count, slave=slave_id)
                client.close()
                return {'success': True, 'message': 'Modbus 读取成功', 'data': result.bits if not result.isError() else None}
            
            elif cmd_type == 'write_coil':
                address = command.get('address', 0)
                value = command.get('value', False)
                result = client.write_coil(address, value, slave=slave_id)
                client.close()
                return {'success': not result.isError(), 'message': 'Modbus 写入成功' if not result.isError() else str(result)}
            
            else:
                client.close()
                return {'success': False, 'message': f'不支持的 Modbus 命令: {cmd_type}'}
                
        except ImportError:
            return {'success': True, 'message': 'Modbus 命令已记录（pymodbus 未安装）'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def _send_http(config: Dict, device_id: int, command: Dict) -> Dict[str, Any]:
        """发送 HTTP 请求"""
        import requests
        
        base_url = config.get('url', 'http://localhost')
        url = f"{base_url}/device/{device_id}/command"
        method = config.get('method', 'POST')
        headers = config.get('headers', {})
        
        try:
            if method == 'POST':
                resp = requests.post(url, json=command, headers=headers, timeout=10)
            elif method == 'PUT':
                resp = requests.put(url, json=command, headers=headers, timeout=10)
            else:
                return {'success': False, 'message': f'不支持的 HTTP 方法: {method}'}
            
            if resp.status_code < 400:
                return {'success': True, 'message': f'HTTP 请求成功: {resp.status_code}', 'topic': url}
            else:
                return {'success': False, 'message': f'HTTP 请求失败: {resp.status_code}'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def get_adapter_statistics(adapter_id: int, user_id: int) -> Dict[str, Any]:
        """获取适配器统计信息"""
        adapter = ProtocolAdapter.query.filter_by(id=adapter_id, user_id=user_id).first()
        if not adapter:
            return {}
        
        # 最近 24 小时的消息统计
        from datetime import timedelta
        since = datetime.utcnow() - timedelta(hours=24)
        
        total_messages = ProtocolMessage.query.filter(
            ProtocolMessage.adapter_id == adapter_id,
            ProtocolMessage.created_at >= since
        ).count()
        
        success_messages = ProtocolMessage.query.filter(
            ProtocolMessage.adapter_id == adapter_id,
            ProtocolMessage.created_at >= since,
            ProtocolMessage.status == 'success'
        ).count()
        
        failed_messages = ProtocolMessage.query.filter(
            ProtocolMessage.adapter_id == adapter_id,
            ProtocolMessage.created_at >= since,
            ProtocolMessage.status == 'failed'
        ).count()
        
        return {
            'adapter_id': adapter_id,
            'name': adapter.name,
            'protocol_type': adapter.protocol_type,
            'is_connected': adapter.is_connected,
            'total_messages': adapter.message_count,
            'total_errors': adapter.error_count,
            'last_24h': {
                'total': total_messages,
                'success': success_messages,
                'failed': failed_messages,
                'success_rate': round(success_messages / total_messages * 100, 2) if total_messages > 0 else 0
            }
        }
