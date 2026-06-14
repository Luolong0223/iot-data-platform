"""
地理围栏与轨迹追踪服务
"""
import json
import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from models.database import db, Geofence, GeofenceAlert, TrackPoint, Device
from flask import current_app


class GeofenceService:
    """地理围栏服务"""
    
    @staticmethod
    def create_geofence(user_id: int, name: str, fence_type: str, 
                       center_lat: float = None, center_lng: float = None, radius: float = None,
                       vertices: List[List[float]] = None,
                       alert_on_enter: bool = True, alert_on_exit: bool = True,
                       alert_severity: str = 'warning',
                       description: str = None) -> Geofence:
        """创建地理围栏"""
        geofence = Geofence(
            user_id=user_id,
            name=name,
            description=description,
            fence_type=fence_type,
            center_lat=center_lat,
            center_lng=center_lng,
            radius=radius,
            vertices=json.dumps(vertices) if vertices else None,
            alert_on_enter=alert_on_enter,
            alert_on_exit=alert_on_exit,
            alert_severity=alert_severity,
            is_enabled=True
        )
        db.session.add(geofence)
        db.session.commit()
        return geofence
    
    @staticmethod
    def update_geofence(geofence_id: int, user_id: int, **kwargs) -> Optional[Geofence]:
        """更新地理围栏"""
        geofence = Geofence.query.filter_by(id=geofence_id, user_id=user_id).first()
        if not geofence:
            return None
        
        for key, value in kwargs.items():
            if hasattr(geofence, key):
                if key == 'vertices' and isinstance(value, list):
                    setattr(geofence, key, json.dumps(value))
                else:
                    setattr(geofence, key, value)
        
        db.session.commit()
        return geofence
    
    @staticmethod
    def delete_geofence(geofence_id: int, user_id: int) -> bool:
        """删除地理围栏"""
        geofence = Geofence.query.filter_by(id=geofence_id, user_id=user_id).first()
        if not geofence:
            return False
        
        db.session.delete(geofence)
        db.session.commit()
        return True
    
    @staticmethod
    def get_geofences(user_id: int, enabled_only: bool = False) -> List[Geofence]:
        """获取用户的所有地理围栏"""
        query = Geofence.query.filter_by(user_id=user_id)
        if enabled_only:
            query = query.filter_by(is_enabled=True)
        return query.order_by(Geofence.created_at.desc()).all()
    
    @staticmethod
    def check_device_in_geofence(device_id: int, lat: float, lng: float, user_id: int) -> List[Dict]:
        """检查设备是否在地理围栏内，返回触发的告警"""
        geofences = Geofence.query.filter_by(user_id=user_id, is_enabled=True).all()
        alerts = []
        
        for geofence in geofences:
            is_inside = GeofenceService._is_point_in_geofence(lat, lng, geofence)
            
            # 检查设备上一次的位置
            last_track = TrackPoint.query.filter_by(
                device_id=device_id, user_id=user_id
            ).order_by(TrackPoint.recorded_at.desc()).first()
            
            if last_track:
                was_inside = GeofenceService._is_point_in_geofence(
                    last_track.latitude, last_track.longitude, geofence
                )
                
                # 进入围栏
                if is_inside and not was_inside and geofence.alert_on_enter:
                    alert = GeofenceService._create_alert(
                        geofence, device_id, user_id, 'enter', lat, lng
                    )
                    alerts.append(alert)
                
                # 离开围栏
                elif not is_inside and was_inside and geofence.alert_on_exit:
                    alert = GeofenceService._create_alert(
                        geofence, device_id, user_id, 'exit', lat, lng
                    )
                    alerts.append(alert)
        
        return alerts
    
    @staticmethod
    def _is_point_in_geofence(lat: float, lng: float, geofence: Geofence) -> bool:
        """检查点是否在地理围栏内"""
        if geofence.fence_type == 'circle':
            return GeofenceService._is_point_in_circle(
                lat, lng, geofence.center_lat, geofence.center_lng, geofence.radius
            )
        elif geofence.fence_type == 'polygon':
            vertices = json.loads(geofence.vertices) if geofence.vertices else []
            return GeofenceService._is_point_in_polygon(lat, lng, vertices)
        return False
    
    @staticmethod
    def _is_point_in_circle(lat: float, lng: float, 
                           center_lat: float, center_lng: float, radius: float) -> bool:
        """检查点是否在圆形区域内（使用Haversine公式）"""
        R = 6371000  # 地球半径（米）
        
        lat1 = math.radians(center_lat)
        lat2 = math.radians(lat)
        delta_lat = math.radians(lat - center_lat)
        delta_lng = math.radians(lng - center_lng)
        
        a = math.sin(delta_lat / 2) ** 2 + \
            math.cos(lat1) * math.cos(lat2) * math.sin(delta_lng / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return distance <= radius
    
    @staticmethod
    def _is_point_in_polygon(lat: float, lng: float, vertices: List[List[float]]) -> bool:
        """检查点是否在多边形内（射线法）"""
        n = len(vertices)
        inside = False
        
        j = n - 1
        for i in range(n):
            if ((vertices[i][0] > lat) != (vertices[j][0] > lat)) and \
               (lng < (vertices[j][1] - vertices[i][1]) * (lat - vertices[i][0]) / 
                (vertices[j][0] - vertices[i][0]) + vertices[i][1]):
                inside = not inside
            j = i
        
        return inside
    
    @staticmethod
    def _create_alert(geofence: Geofence, device_id: int, user_id: int,
                     alert_type: str, lat: float, lng: float) -> GeofenceAlert:
        """创建地理围栏告警"""
        device = Device.query.get(device_id)
        device_name = device.name if device else f"设备{device_id}"
        
        if alert_type == 'enter':
            message = f"{device_name} 进入围栏 {geofence.name}"
        else:
            message = f"{device_name} 离开围栏 {geofence.name}"
        
        alert = GeofenceAlert(
            geofence_id=geofence.id,
            device_id=device_id,
            user_id=user_id,
            alert_type=alert_type,
            device_lat=lat,
            device_lng=lng,
            message=message,
            severity=geofence.alert_severity,
            is_read=False
        )
        db.session.add(alert)
        db.session.commit()
        return alert
    
    @staticmethod
    def get_alerts(user_id: int, geofence_id: int = None, device_id: int = None,
                  unread_only: bool = False, limit: int = 100) -> List[GeofenceAlert]:
        """获取地理围栏告警"""
        query = GeofenceAlert.query.filter_by(user_id=user_id)
        
        if geofence_id:
            query = query.filter_by(geofence_id=geofence_id)
        if device_id:
            query = query.filter_by(device_id=device_id)
        if unread_only:
            query = query.filter_by(is_read=False)
        
        return query.order_by(GeofenceAlert.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def mark_alert_read(alert_id: int, user_id: int) -> bool:
        """标记告警为已读"""
        alert = GeofenceAlert.query.filter_by(id=alert_id, user_id=user_id).first()
        if not alert:
            return False
        
        alert.is_read = True
        db.session.commit()
        return True


class TrackService:
    """轨迹追踪服务"""
    
    @staticmethod
    def add_track_point(device_id: int, user_id: int, latitude: float, longitude: float,
                       altitude: float = None, speed: float = None, heading: float = None,
                       accuracy: float = None, recorded_at: datetime = None,
                       metadata: Dict = None) -> TrackPoint:
        """添加轨迹点"""
        track_point = TrackPoint(
            device_id=device_id,
            user_id=user_id,
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            speed=speed,
            heading=heading,
            accuracy=accuracy,
            recorded_at=recorded_at or datetime.utcnow(),
            track_metadata=json.dumps(metadata) if metadata else None
        )
        db.session.add(track_point)
        db.session.commit()
        
        # 检查地理围栏
        GeofenceService.check_device_in_geofence(device_id, latitude, longitude, user_id)
        
        return track_point
    
    @staticmethod
    def get_track(device_id: int, user_id: int, start_time: datetime = None,
                 end_time: datetime = None, limit: int = 1000) -> List[TrackPoint]:
        """获取设备轨迹"""
        query = TrackPoint.query.filter_by(device_id=device_id, user_id=user_id)
        
        if start_time:
            query = query.filter(TrackPoint.recorded_at >= start_time)
        if end_time:
            query = query.filter(TrackPoint.recorded_at <= end_time)
        
        return query.order_by(TrackPoint.recorded_at.asc()).limit(limit).all()
    
    @staticmethod
    def get_latest_position(device_id: int, user_id: int) -> Optional[TrackPoint]:
        """获取设备最新位置"""
        return TrackPoint.query.filter_by(
            device_id=device_id, user_id=user_id
        ).order_by(TrackPoint.recorded_at.desc()).first()
    
    @staticmethod
    def get_track_statistics(device_id: int, user_id: int, 
                            start_time: datetime = None, end_time: datetime = None) -> Dict:
        """获取轨迹统计信息"""
        query = TrackPoint.query.filter_by(device_id=device_id, user_id=user_id)
        
        if start_time:
            query = query.filter(TrackPoint.recorded_at >= start_time)
        if end_time:
            query = query.filter(TrackPoint.recorded_at <= end_time)
        
        points = query.order_by(TrackPoint.recorded_at.asc()).all()
        
        if not points:
            return {
                'total_points': 0,
                'total_distance': 0,
                'duration': 0,
                'avg_speed': 0,
                'max_speed': 0
            }
        
        # 计算总距离
        total_distance = 0
        max_speed = 0
        
        for i in range(1, len(points)):
            distance = TrackService._calculate_distance(
                points[i-1].latitude, points[i-1].longitude,
                points[i].latitude, points[i].longitude
            )
            total_distance += distance
            
            if points[i].speed and points[i].speed > max_speed:
                max_speed = points[i].speed
        
        # 计算时长
        duration = (points[-1].recorded_at - points[0].recorded_at).total_seconds()
        
        # 计算平均速度
        avg_speed = (total_distance / duration) if duration > 0 else 0
        
        return {
            'total_points': len(points),
            'total_distance': round(total_distance, 2),  # 米
            'duration': round(duration, 2),  # 秒
            'avg_speed': round(avg_speed, 2),  # m/s
            'max_speed': round(max_speed, 2)  # m/s
        }
    
    @staticmethod
    def _calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """计算两点之间的距离（Haversine公式）"""
        R = 6371000  # 地球半径（米）
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = math.sin(delta_lat / 2) ** 2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    @staticmethod
    def cleanup_old_tracks(days: int = 30) -> int:
        """清理旧轨迹数据"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted = TrackPoint.query.filter(TrackPoint.recorded_at < cutoff_date).delete()
        db.session.commit()
        return deleted
