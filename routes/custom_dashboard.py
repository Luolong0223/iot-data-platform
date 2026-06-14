"""
自定义大屏 API 路由
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.dashboard_service import DashboardService

custom_dashboard_bp = Blueprint('custom_dashboard', __name__, url_prefix='/api/dashboards')


@custom_dashboard_bp.route('', methods=['GET'])
@login_required
def get_layouts():
    """获取所有大屏布局"""
    layouts = DashboardService.get_layouts(current_user.id)
    return jsonify({
        'success': True,
        'data': layouts,
        'count': len(layouts)
    })


@custom_dashboard_bp.route('/<int:layout_id>', methods=['GET'])
@login_required
def get_layout(layout_id):
    """获取单个大屏布局"""
    layout = DashboardService.get_layout(layout_id, current_user.id)
    if not layout:
        return jsonify({'success': False, 'error': '大屏不存在'}), 404
    return jsonify({'success': True, 'data': layout})


@custom_dashboard_bp.route('', methods=['POST'])
@login_required
def create_layout():
    """创建大屏布局"""
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'success': False, 'error': '缺少 name 参数'}), 400
    
    result = DashboardService.create_layout(
        user_id=current_user.id,
        name=data['name'],
        description=data.get('description'),
        layout_config=data.get('layout_config', []),
        is_default=data.get('is_default', False),
        visibility=data.get('visibility', 'private'),
        theme_config=data.get('theme_config', {})
    )
    
    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 500


@custom_dashboard_bp.route('/<int:layout_id>', methods=['PUT'])
@login_required
def update_layout(layout_id):
    """更新大屏布局"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '缺少请求数据'}), 400
    
    result = DashboardService.update_layout(layout_id, current_user.id, **data)
    
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400 if '不存在' in result.get('error', '') else 500


@custom_dashboard_bp.route('/<int:layout_id>', methods=['DELETE'])
@login_required
def delete_layout(layout_id):
    """删除大屏布局"""
    result = DashboardService.delete_layout(layout_id, current_user.id)
    
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400 if '不存在' in result.get('error', '') else 500


@custom_dashboard_bp.route('/<int:layout_id>/duplicate', methods=['POST'])
@login_required
def duplicate_layout(layout_id):
    """复制大屏布局"""
    data = request.get_json() or {}
    new_name = data.get('name', '副本')
    
    result = DashboardService.duplicate_layout(layout_id, current_user.id, new_name)
    
    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 400


@custom_dashboard_bp.route('/<int:layout_id>/widgets', methods=['POST'])
@login_required
def add_widget(layout_id):
    """添加组件到大屏"""
    data = request.get_json()
    if not data or 'widget_type' not in data:
        return jsonify({'success': False, 'error': '缺少 widget_type 参数'}), 400
    
    result = DashboardService.add_widget(
        layout_id=layout_id,
        user_id=current_user.id,
        widget_type=data['widget_type'],
        title=data.get('title'),
        x=data.get('x', 0),
        y=data.get('y', 0),
        w=data.get('w', 4),
        h=data.get('h', 3),
        data_config=data.get('data_config', {}),
        style_config=data.get('style_config', {}),
        refresh_interval=data.get('refresh_interval', 30),
        order=data.get('order', 0)
    )
    
    if result['success']:
        return jsonify(result), 201
    return jsonify(result), 500


@custom_dashboard_bp.route('/widgets/<int:widget_id>', methods=['PUT'])
@login_required
def update_widget(widget_id):
    """更新组件"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '缺少请求数据'}), 400
    
    result = DashboardService.update_widget(widget_id, current_user.id, **data)
    
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400 if '不存在' in result.get('error', '') else 500


@custom_dashboard_bp.route('/widgets/<int:widget_id>', methods=['DELETE'])
@login_required
def delete_widget(widget_id):
    """删除组件"""
    result = DashboardService.delete_widget(widget_id, current_user.id)
    
    if result['success']:
        return jsonify(result)
    return jsonify(result), 400 if '不存在' in result.get('error', '') else 500


@custom_dashboard_bp.route('/<int:layout_id>/positions', methods=['PUT'])
@login_required
def update_positions(layout_id):
    """批量更新组件位置（拖拽后保存）"""
    data = request.get_json()
    if not data or 'positions' not in data:
        return jsonify({'success': False, 'error': '缺少 positions 参数'}), 400
    
    result = DashboardService.update_layout_positions(
        layout_id, current_user.id, data['positions']
    )
    
    if result['success']:
        return jsonify(result)
    return jsonify(result), 500
