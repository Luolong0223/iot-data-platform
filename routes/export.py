"""
数据导出路由 - 提供数据导出下载接口
"""
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from services.data_export import DataExportService

logger = logging.getLogger(__name__)

export_bp = Blueprint('export', __name__, url_prefix='/api/export')


@export_bp.route('/data/csv', methods=['GET'])
@login_required
def export_data_csv():
    """导出数据点到CSV文件"""
    try:
        # 获取查询参数
        device_id = request.args.get('device_id', type=int)
        channel_id = request.args.get('channel_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', default=10000, type=int)
        
        # 限制最大导出数量
        max_limit = current_app.config.get('EXPORT_MAX_ROWS', 100000)
        limit = min(limit, max_limit)
        
        # 解析时间
        start_time = None
        end_time = None
        if start_date:
            try:
                start_time = datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                pass
        if end_date:
            try:
                end_time = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            except ValueError:
                pass
        
        # 导出数据
        csv_content = DataExportService.export_data_points_to_csv(
            user_id=current_user.id,
            device_id=device_id,
            channel_id=channel_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        # 生成文件名
        filename = f'data_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return DataExportService.generate_response(
            csv_content,
            filename,
            'text/csv; charset=utf-8-sig'
        )
        
    except Exception as e:
        logger.error(f"Export data CSV failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@export_bp.route('/data/excel', methods=['GET'])
@login_required
def export_data_excel():
    """导出数据点到Excel文件"""
    try:
        # 获取查询参数
        device_id = request.args.get('device_id', type=int)
        channel_id = request.args.get('channel_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', default=10000, type=int)
        
        # 限制最大导出数量
        max_limit = current_app.config.get('EXPORT_MAX_ROWS', 100000)
        limit = min(limit, max_limit)
        
        # 解析时间
        start_time = None
        end_time = None
        if start_date:
            try:
                start_time = datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                pass
        if end_date:
            try:
                end_time = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            except ValueError:
                pass
        
        # 导出数据
        excel_content = DataExportService.export_data_points_to_excel(
            user_id=current_user.id,
            device_id=device_id,
            channel_id=channel_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        # 生成文件名
        filename = f'data_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        response = DataExportService.generate_response(
            excel_content,
            filename,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        return response
        
    except ImportError:
        return jsonify({'success': False, 'message': 'Excel导出功能未安装，请安装openpyxl'}), 500
    except Exception as e:
        logger.error(f"Export data Excel failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@export_bp.route('/devices/excel', methods=['GET'])
@login_required
def export_devices_excel():
    """导出设备列表到Excel"""
    try:
        excel_content = DataExportService.export_devices_to_excel(current_user.id)
        
        filename = f'devices_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        response = DataExportService.generate_response(
            excel_content,
            filename,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        return response
        
    except ImportError:
        return jsonify({'success': False, 'message': 'Excel导出功能未安装'}), 500
    except Exception as e:
        logger.error(f"Export devices failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@export_bp.route('/alarms/excel', methods=['GET'])
@login_required
def export_alarms_excel():
    """导出报警记录到Excel"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        is_read = request.args.get('is_read', type=lambda v: v.lower() == 'true' if v else None)
        
        start_time = None
        end_time = None
        if start_date:
            try:
                start_time = datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                pass
        if end_date:
            try:
                end_time = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            except ValueError:
                pass
        
        excel_content = DataExportService.export_alarms_to_excel(
            user_id=current_user.id,
            start_time=start_time,
            end_time=end_time,
            is_read=is_read
        )
        
        filename = f'alarms_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        response = DataExportService.generate_response(
            excel_content,
            filename,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        return response
        
    except ImportError:
        return jsonify({'success': False, 'message': 'Excel导出功能未安装'}), 500
    except Exception as e:
        logger.error(f"Export alarms failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
