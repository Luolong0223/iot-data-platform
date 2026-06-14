"""
数据可视化路由 - 拓扑图、热力图、GIS地图
"""
from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from services.visualization import TopologyService, HeatmapService, GISMapService
def success_response(data=None, msg='操作成功'):
    return {'success': True, 'data': data, 'msg': msg}

def error_response(msg='操作失败', code=400):
    return {'success': False, 'msg': msg}, code

viz_bp = Blueprint('viz', __name__, url_prefix='/api/visualization')


@viz_bp.route('/topology')
@login_required
def topology_page():
    """设备拓扑图页面"""
    return render_template('visualization/topology.html')


@viz_bp.route('/heatmap')
@login_required
def heatmap_page():
    """数据点热力图页面"""
    return render_template('visualization/heatmap.html')


@viz_bp.route('/gis-map')
@login_required
def gis_map_page():
    """GIS 地图页面"""
    return render_template('visualization/gis_map.html')


@viz_bp.route('/index')
@login_required
def viz_index_page():
    """可视化中心主页"""
    return render_template('visualization/index.html')


# ---------------- API ----------------

@viz_bp.route('/topology', methods=['GET'])
@login_required
def api_topology():
    """获取拓扑图数据"""
    try:
        group_id = request.args.get('group_id', type=int)
        topology = TopologyService.build_topology(current_user.id, group_id)
        return success_response(topology)
    except Exception as e:
        return error_response(f'获取拓扑图失败: {str(e)}')


@viz_bp.route('/topology/path/<int:device_id>', methods=['GET'])
@login_required
def api_device_path(device_id):
    """获取设备到根节点的路径"""
    try:
        path = TopologyService.get_device_path(current_user.id, device_id)
        return success_response({
            'path': [{'id': p.id, 'name': p.name, 'type': type(p).__name__} for p in path]
        })
    except Exception as e:
        return error_response(str(e))


@viz_bp.route('/heatmap/points', methods=['GET'])
@login_required
def api_point_heatmap():
    """数据点活跃度热力图"""
    try:
        period = request.args.get('period', '24h')
        data = HeatmapService.get_data_point_heatmap(current_user.id, period)
        return success_response(data)
    except Exception as e:
        return error_response(str(e))


@viz_bp.route('/heatmap/devices', methods=['GET'])
@login_required
def api_device_heatmap():
    """设备活跃度热力图"""
    try:
        days = request.args.get('days', 7, type=int)
        data = HeatmapService.get_device_activity_heatmap(current_user.id, days)
        return success_response(data)
    except Exception as e:
        return error_response(str(e))


@viz_bp.route('/map/devices', methods=['GET'])
@login_required
def api_map_devices():
    """地图设备数据"""
    try:
        data = GISMapService.get_device_map_data(current_user.id)
        return success_response(data)
    except Exception as e:
        return error_response(str(e))


@viz_bp.route('/geofence', methods=['POST'])
@login_required
def api_geofence():
    """地理围栏检查"""
    try:
        body = request.get_json() or {}
        lat = body.get('lat', type=float)
        lng = body.get('lng', type=float)
        radius = body.get('radius_km', 1.0, type=float)
        if lat is None or lng is None:
            return error_response('缺少经纬度参数')
        data = GISMapService.get_geofence_status(current_user.id, lat, lng, radius)
        return success_response(data)
    except Exception as e:
        return error_response(str(e))

@viz_bp.route('/distribution', methods=['GET'])
@login_required
def api_distribution():
    """数据点分布统计"""
    try:
        from services.visualization import HeatmapService
        data = HeatmapService.get_data_point_heatmap(current_user.id)
        return success_response(data)
    except Exception as e:
        return error_response(str(e), 500)
