"""
数据可视化服务 - 拓扑图、热力图、GIS地图
Data Visualization Service - Topology, Heatmap, GIS Map
"""
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, case
from collections import defaultdict
import json
import math


class TopologyService:
    """设备拓扑图服务"""

    @staticmethod
    def build_topology(user_id, group_id=None, max_nodes=200):
        """
        构建设备拓扑图数据
        返回节点（设备/分组）和边（父子关系/数据流向）
        """
        from models.database import db, Project, DeviceGroup, Device, Channel, DataPoint

        # 获取分组
        groups_query = DeviceGroup.query.filter_by(user_id=user_id)
        if group_id:
            groups_query = groups_query.filter_by(id=group_id)
        groups = groups_query.all()

        # 获取设备
        devices = Device.query.filter_by(user_id=user_id).limit(max_nodes).all()

        nodes = []
        edges = []

        # 根节点（中心）
        nodes.append({
            'id': 'root',
            'label': '根节点',
            'type': 'root',
            'symbol': 'roundRect',
            'symbolSize': [80, 40],
            'itemStyle': {'color': '#5470c6'}
        })

        # 分组节点
        for g in groups:
            nodes.append({
                'id': f'group_{g.id}',
                'label': g.name,
                'type': 'group',
                'symbol': 'rect',
                'symbolSize': [70, 36],
                'itemStyle': {
                    'color': g.is_online if hasattr(g, 'is_online') else '#91cc75'
                },
                'category': 1
            })
            edges.append({
                'source': 'root',
                'target': f'group_{g.id}'
            })

            # 父分组关系
            if g.parent_id:
                edges.append({
                    'source': f'group_{g.parent_id}',
                    'target': f'group_{g.id}',
                    'lineStyle': {'type': 'dashed', 'color': '#aaa'}
                })

        # 设备节点
        for d in devices:
            nodes.append({
                'id': f'device_{d.id}',
                'label': d.name,
                'type': 'device',
                'symbol': 'circle',
                'symbolSize': 28,
                'itemStyle': {
                    'color': '#67c23a' if d.is_online else '#f56c6c',
                    'borderColor': '#fff',
                    'borderWidth': 2
                },
                'category': 2,
                'is_online': d.is_online,
                'device_key': d.device_key
            })
            # 设备属于哪个分组
            if d.group_id:
                edges.append({
                    'source': f'group_{d.group_id}',
                    'target': f'device_{d.id}'
                })
            else:
                edges.append({
                    'source': 'root',
                    'target': f'device_{d.id}'
                })

        # 通道作为设备子节点（采样：每个设备最多展示前 3 个通道）
        for d in devices[:50]:  # 限制数量，避免太密
            channels = Channel.query.filter_by(device_id=d.id).limit(3).all()
            for ch in channels:
                nodes.append({
                    'id': f'channel_{ch.id}',
                    'label': ch.name or f'CH-{ch.id}',
                    'type': 'channel',
                    'symbol': 'diamond',
                    'symbolSize': 18,
                    'itemStyle': {
                        'color': '#e6a23c' if ch.is_online else '#909399'
                    },
                    'category': 3
                })
                edges.append({
                    'source': f'device_{d.id}',
                    'target': f'channel_{ch.id}',
                    'lineStyle': {'color': '#ddd', 'width': 1}
                })

        return {
            'nodes': nodes,
            'edges': edges,
            'categories': [
                {'name': '根'},
                {'name': '分组'},
                {'name': '设备'},
                {'name': '通道'}
            ]
        }

    @staticmethod
    def get_device_path(user_id, device_id):
        """获取设备到根节点的路径"""
        from models.database import db, Device, DeviceGroup
        device = Device.query.filter_by(id=device_id, user_id=user_id).first()
        if not device:
            return []

        path = [device]
        group = device.group
        while group:
            path.append(group)
            if group.parent:
                group = group.parent
            else:
                group = None
        return path


class HeatmapService:
    """热力图服务"""

    @staticmethod
    def get_data_point_heatmap(user_id, period='24h', metric='count'):
        """
        数据点活跃度热力图
        横轴：小时（0-23），纵轴：数据点名称
        """
        from models.database import db, DataPoint, Channel, Device
        from datetime import datetime, timedelta

        # 时间范围
        now = datetime.now()
        if period == '24h':
            start_time = now - timedelta(hours=24)
            hours = 24
        elif period == '7d':
            start_time = now - timedelta(days=7)
            hours = 168
        else:
            start_time = now - timedelta(hours=24)
            hours = 24

        # 获取用户设备的所有数据点
        device_ids = [d.id for d in Device.query.filter_by(user_id=user_id).all()]
        if not device_ids:
            return {'hours': list(range(24)), 'points': [], 'data': []}

        channel_ids = [c.id for c in Channel.query.filter(Channel.device_id.in_(device_ids)).all()]

        # 聚合查询（按小时+数据点名称）
        rows = db.session.query(
            func.strftime('%H', DataPoint.timestamp).label('hour'),
            DataPoint.name,
            func.count(DataPoint.id).label('cnt')
        ).filter(
            DataPoint.channel_id.in_(channel_ids),
            DataPoint.timestamp >= start_time
        ).group_by('hour', DataPoint.name).all()

        # 整理数据
        point_names = sorted({r.name for r in rows})[:20]  # 最多 20 个数据点
        heatmap = [[0]*hours for _ in point_names]
        point_idx = {n: i for i, n in enumerate(point_names)}

        for r in rows:
            h = int(r.hour)
            if r.name in point_idx and h < hours:
                heatmap[point_idx[r.name]][h] = r.cnt

        return {
            'hours': list(range(hours)),
            'points': point_names,
            'data': heatmap
        }

    @staticmethod
    def get_device_activity_heatmap(user_id, days=7):
        """
        设备活跃度热力图
        横轴：小时（0-23），纵轴：日期
        """
        from models.database import db, DataPoint, Channel, Device
        now = datetime.now()
        start_time = now - timedelta(days=days)

        device_ids = [d.id for d in Device.query.filter_by(user_id=user_id).all()]
        if not device_ids:
            return {'days': [], 'hours': list(range(24)), 'data': []}

        channel_ids = [c.id for c in Channel.query.filter(Channel.device_id.in_(device_ids)).all()]

        rows = db.session.query(
            func.date(DataPoint.timestamp).label('day'),
            func.strftime('%H', DataPoint.timestamp).label('hour'),
            func.count(DataPoint.id).label('cnt')
        ).filter(
            DataPoint.channel_id.in_(channel_ids),
            DataPoint.timestamp >= start_time
        ).group_by('day', 'hour').all()

        # 按日期分组
        days_set = sorted({str(r.day) for r in rows})
        day_idx = {d: i for i, d in enumerate(days_set)}
        data = [[0]*24 for _ in days_set]

        for r in rows:
            d = str(r.day)
            if d in day_idx:
                h = int(r.hour)
                data[day_idx[d]][h] = r.cnt

        return {
            'days': days_set,
            'hours': list(range(24)),
            'data': data
        }


class GISMapService:
    """GIS 地图聚合服务"""

    @staticmethod
    def get_device_map_data(user_id):
        """获取设备地图数据（含聚合信息）"""
        from models.database import db, Device
        devices = Device.query.filter(
            Device.user_id == user_id,
            Device.latitude.isnot(None),
            Device.longitude.isnot(None)
        ).all()

        points = []
        for d in devices:
            if d.latitude and d.longitude:
                points.append({
                    'id': d.id,
                    'name': d.name,
                    'lat': float(d.latitude),
                    'lng': float(d.longitude),
                    'location': d.location_name or '未知位置',
                    'is_online': d.is_online,
                    'last_seen': d.last_seen_at.isoformat() if d.last_seen_at else None,
                    'voltage_mv': d.voltage_mv
                })

        # 简单聚合：按 location_name 分组
        groups = defaultdict(list)
        for p in points:
            groups[p['location']].append(p)

        clusters = []
        for location, pts in groups.items():
            if len(pts) > 1:
                # 计算中心点
                avg_lat = sum(p['lat'] for p in pts) / len(pts)
                avg_lng = sum(p['lng'] for p in pts) / len(pts)
                clusters.append({
                    'lat': avg_lat,
                    'lng': avg_lng,
                    'count': len(pts),
                    'location': location,
                    'device_ids': [p['id'] for p in pts]
                })

        return {
            'points': points,
            'clusters': clusters,
            'total': len(points),
            'online': sum(1 for p in points if p['is_online']),
            'bounds': {
                'min_lat': min((p['lat'] for p in points), default=None),
                'max_lat': max((p['lat'] for p in points), default=None),
                'min_lng': min((p['lng'] for p in points), default=None),
                'max_lng': max((p['lng'] for p in points), default=None),
            }
        }

    @staticmethod
    def get_geofence_status(user_id, fence_lat, fence_lng, radius_km=1.0):
        """检查设备是否在地理围栏内"""
        from models.database import db, Device
        devices = Device.query.filter(
            Device.user_id == user_id,
            Device.latitude.isnot(None),
            Device.longitude.isnot(None)
        ).all()

        in_fence = []
        out_fence = []
        for d in devices:
            if d.latitude and d.longitude:
                # Haversine 距离
                lat1, lng1 = math.radians(fence_lat), math.radians(fence_lng)
                lat2, lng2 = math.radians(float(d.latitude)), math.radians(float(d.longitude))
                dlat = lat2 - lat1
                dlng = lng2 - lng1
                a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
                c = 2 * math.asin(math.sqrt(a))
                distance_km = 6371 * c  # 地球半径
                if distance_km <= radius_km:
                    in_fence.append({'id': d.id, 'name': d.name, 'distance_km': distance_km})
                else:
                    out_fence.append({'id': d.id, 'name': d.name, 'distance_km': distance_km})

        return {
            'fence': {'lat': fence_lat, 'lng': fence_lng, 'radius_km': radius_km},
            'in_count': len(in_fence),
            'out_count': len(out_fence),
            'in_fence': in_fence,
            'out_fence': out_fence
        }
