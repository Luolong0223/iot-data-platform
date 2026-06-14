"""设备模拟器服务 - 虚拟设备数据生成与测试"""
import random
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class DeviceSimulator:
    """设备模拟器 - 生成虚拟设备数据"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.running_simulators: Dict[int, dict] = {}  # simulator_id -> config
        self.threads: Dict[int, threading.Thread] = {}
    
    def create_simulator(self, user_id: int, device_id: int, config: dict) -> dict:
        """创建设备模拟器"""
        simulator_id = len(self.running_simulators) + 1
        
        simulator_config = {
            'id': simulator_id,
            'user_id': user_id,
            'device_id': device_id,
            'metrics': config.get('metrics', ['temperature', 'humidity', 'voltage']),
            'interval': config.get('interval', 5),  # 秒
            'data_range': config.get('data_range', {
                'temperature': {'min': 20, 'max': 40},
                'humidity': {'min': 40, 'max': 80},
                'voltage': {'min': 3000, 'max': 3600}
            }),
            'noise': config.get('noise', 0.1),  # 噪声比例
            'is_running': False,
            'created_at': datetime.utcnow().isoformat()
        }
        
        self.running_simulators[simulator_id] = simulator_config
        return simulator_config
    
    def start_simulator(self, simulator_id: int) -> bool:
        """启动模拟器"""
        if simulator_id not in self.running_simulators:
            return False
        
        config = self.running_simulators[simulator_id]
        if config['is_running']:
            return True
        
        config['is_running'] = True
        
        # 启动数据生成线程
        thread = threading.Thread(
            target=self._generate_data_loop,
            args=(simulator_id,),
            daemon=True
        )
        thread.start()
        self.threads[simulator_id] = thread
        
        logger.info(f"Simulator {simulator_id} started")
        return True
    
    def stop_simulator(self, simulator_id: int) -> bool:
        """停止模拟器"""
        if simulator_id not in self.running_simulators:
            return False
        
        config = self.running_simulators[simulator_id]
        config['is_running'] = False
        
        logger.info(f"Simulator {simulator_id} stopped")
        return True
    
    def delete_simulator(self, simulator_id: int) -> bool:
        """删除模拟器"""
        if simulator_id not in self.running_simulators:
            return False
        
        self.stop_simulator(simulator_id)
        del self.running_simulators[simulator_id]
        
        if simulator_id in self.threads:
            del self.threads[simulator_id]
        
        logger.info(f"Simulator {simulator_id} deleted")
        return True
    
    def get_simulator(self, simulator_id: int) -> Optional[dict]:
        """获取模拟器配置"""
        return self.running_simulators.get(simulator_id)
    
    def list_simulators(self, user_id: int = None) -> List[dict]:
        """列出所有模拟器"""
        simulators = list(self.running_simulators.values())
        if user_id:
            simulators = [s for s in simulators if s['user_id'] == user_id]
        return simulators
    
    def _generate_data_loop(self, simulator_id: int):
        """数据生成循环"""
        config = self.running_simulators.get(simulator_id)
        if not config:
            return
        
        from models.database import db, DataPoint, SlaveChannel, Device
        from flask import current_app
        
        while config['is_running']:
            try:
                # 为每个指标生成数据
                for metric in config['metrics']:
                    data_range = config['data_range'].get(metric, {'min': 0, 'max': 100})
                    
                    # 生成基础值 + 噪声
                    base_value = random.uniform(data_range['min'], data_range['max'])
                    noise = random.uniform(-1, 1) * config['noise'] * (data_range['max'] - data_range['min'])
                    value = base_value + noise
                    
                    # 创建数据点（需要在应用上下文中）
                    try:
                        from app import create_app
                        app = create_app()
                        with app.app_context():
                            # 查找或创建通道
                            channel = SlaveChannel.query.filter_by(
                                device_id=config['device_id'],
                                name=metric
                            ).first()
                            
                            if not channel:
                                channel = SlaveChannel(
                                    device_id=config['device_id'],
                                    name=metric
                                )
                                db.session.add(channel)
                                db.session.commit()
                            
                            # 创建数据点
                            data_point = DataPoint(
                                channel_id=channel.id,
                                name=metric,
                                value=round(value, 2),
                                timestamp=datetime.utcnow()
                            )
                            db.session.add(data_point)
                            db.session.commit()
                    except Exception as e:
                        logger.error(f"Failed to create data point: {e}")
                
                # 等待指定间隔
                time.sleep(config['interval'])
                
            except Exception as e:
                logger.error(f"Simulator {simulator_id} error: {e}")
                time.sleep(1)
    
    def _get_unit(self, metric: str) -> str:
        """获取指标单位"""
        units = {
            'temperature': '°C',
            'humidity': '%',
            'voltage': 'mV',
            'current': 'mA',
            'pressure': 'kPa',
            'light': 'lux'
        }
        return units.get(metric, '')
    
    def generate_single_data(self, device_id: int, metric: str, value: float = None) -> dict:
        """生成单条数据（手动触发）"""
        if value is None:
            # 根据指标类型生成默认值
            ranges = {
                'temperature': (20, 40),
                'humidity': (40, 80),
                'voltage': (3000, 3600),
                'current': (100, 500),
                'pressure': (95, 105),
                'light': (100, 1000)
            }
            min_val, max_val = ranges.get(metric, (0, 100))
            value = random.uniform(min_val, max_val)
        
        return {
            'device_id': device_id,
            'metric': metric,
            'value': round(value, 2),
            'timestamp': datetime.utcnow().isoformat()
        }


# 全局实例
simulator = DeviceSimulator()
