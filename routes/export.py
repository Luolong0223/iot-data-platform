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


@export_bp.route('/data/json', methods=['GET'])
@login_required
def export_data_json():
    """导出数据点到JSON文件"""
    try:
        device_id = request.args.get('device_id', type=int)
        channel_id = request.args.get('channel_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', default=10000, type=int)
        
        max_limit = current_app.config.get('EXPORT_MAX_ROWS', 100000)
        limit = min(limit, max_limit)
        
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
        
        json_content = DataExportService.export_data_points_to_json(
            user_id=current_user.id,
            device_id=device_id,
            channel_id=channel_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        filename = f'data_points_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        response = DataExportService.generate_response(
            json_content.encode('utf-8'),
            filename,
            'application/json'
        )
        return response
        
    except Exception as e:
        logger.error(f"Export data to JSON failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@export_bp.route('/devices/json', methods=['GET'])
@login_required
def export_devices_json():
    """导出设备列表到JSON"""
    try:
        json_content = DataExportService.export_devices_to_json(user_id=current_user.id)
        filename = f'devices_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        response = DataExportService.generate_response(
            json_content.encode('utf-8'),
            filename,
            'application/json'
        )
        return response
    except Exception as e:
        logger.error(f"Export devices to JSON failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@export_bp.route('/alarms/json', methods=['GET'])
@login_required
def export_alarms_json():
    """导出报警记录到JSON"""
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
        
        json_content = DataExportService.export_alarms_to_json(
            user_id=current_user.id,
            start_time=start_time,
            end_time=end_time,
            is_read=is_read
        )
        
        filename = f'alarms_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        response = DataExportService.generate_response(
            json_content.encode('utf-8'),
            filename,
            'application/json'
        )
        return response
    except Exception as e:
        logger.error(f"Export alarms to JSON failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@export_bp.route('/rules/json', methods=['GET'])
@login_required
def export_rules_json():
    """导出规则引擎配置到JSON"""
    try:
        json_content = DataExportService.export_rules_to_json(user_id=current_user.id)
        filename = f'rules_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        response = DataExportService.generate_response(
            json_content.encode('utf-8'),
            filename,
            'application/json'
        )
        return response
    except Exception as e:
        logger.error(f"Export rules to JSON failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@export_bp.route('/batch', methods=['POST'])
@login_required
def batch_export():
    """批量导出多种数据"""
    try:
        import zipfile
        import io
        
        data = request.get_json() or {}
        export_types = data.get('types', ['devices', 'alarms', 'rules'])
        format_type = data.get('format', 'json')  # json or excel
        
        # 创建 ZIP 文件
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if 'devices' in export_types:
                if format_type == 'json':
                    content = DataExportService.export_devices_to_json(current_user.id)
                    zip_file.writestr(f'devices_{timestamp}.json', content)
                else:
                    content = DataExportService.export_devices_to_excel(current_user.id)
                    zip_file.writestr(f'devices_{timestamp}.xlsx', content)
            
            if 'alarms' in export_types:
                if format_type == 'json':
                    content = DataExportService.export_alarms_to_json(current_user.id)
                    zip_file.writestr(f'alarms_{timestamp}.json', content)
                else:
                    content = DataExportService.export_alarms_to_excel(current_user.id)
                    zip_file.writestr(f'alarms_{timestamp}.xlsx', content)
            
            if 'rules' in export_types:
                content = DataExportService.export_rules_to_json(current_user.id)
                zip_file.writestr(f'rules_{timestamp}.json', content)
            
            if 'data' in export_types:
                device_id = data.get('device_id')
                limit = data.get('limit', 10000)
                if format_type == 'json':
                    content = DataExportService.export_data_points_to_json(
                        current_user.id, device_id=device_id, limit=limit
                    )
                    zip_file.writestr(f'data_points_{timestamp}.json', content)
                else:
                    content = DataExportService.export_data_points_to_excel(
                        current_user.id, device_id=device_id, limit=limit
                    )
                    zip_file.writestr(f'data_points_{timestamp}.xlsx', content)
        
        zip_buffer.seek(0)
        filename = f'iot_export_{timestamp}.zip'
        response = DataExportService.generate_response(
            zip_buffer.getvalue(),
            filename,
            'application/zip'
        )
        return response
        
    except Exception as e:
        logger.error(f"Batch export failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
