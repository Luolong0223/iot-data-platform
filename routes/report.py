"""
数据聚合报表路由
Data Aggregation Report Routes
"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.report_service import ReportService, ReportScheduleService

logger = logging.getLogger(__name__)

report_bp = Blueprint('report', __name__, url_prefix='/api/report')


# ========================================================================
# 报表管理
# ========================================================================

@report_bp.route('/reports', methods=['POST'])
@login_required
def create_report():
    """创建报表"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        name = data.get('name')
        report_type = data.get('report_type', 'custom')
        period_start = data.get('period_start')
        period_end = data.get('period_end')
        
        if not all([name, period_start, period_end]):
            return jsonify({'success': False, 'message': '缺少必填字段'}), 400
        
        # 解析日期
        start = datetime.fromisoformat(period_start.replace('Z', '+00:00'))
        end = datetime.fromisoformat(period_end.replace('Z', '+00:00'))
        
        report = ReportService.create_report(
            user_id=current_user.id,
            name=name,
            report_type=report_type,
            period_start=start,
            period_end=end
        )
        
        return jsonify({
            'success': True,
            'message': '报表创建成功',
            'report': report.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"创建报表失败: {e}")
        return jsonify({'success': False, 'message': '创建报表失败'}), 500


@report_bp.route('/reports/<int:report_id>/generate', methods=['POST'])
@login_required
def generate_report(report_id):
    """生成报表数据"""
    try:
        report = ReportService.generate_report(report_id, current_user.id)
        
        return jsonify({
            'success': True,
            'message': '报表生成完成',
            'report': report.to_dict()
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"生成报表失败: {e}")
        return jsonify({'success': False, 'message': '生成报表失败'}), 500


@report_bp.route('/reports/daily', methods=['POST'])
@login_required
def generate_daily_report():
    """生成日报"""
    try:
        data = request.get_json() or {}
        date_str = data.get('date')
        
        date = None
        if date_str:
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        
        report = ReportService.generate_daily_report(current_user.id, date)
        
        return jsonify({
            'success': True,
            'message': '日报生成完成',
            'report': report.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"生成日报失败: {e}")
        return jsonify({'success': False, 'message': '生成日报失败'}), 500


@report_bp.route('/reports/weekly', methods=['POST'])
@login_required
def generate_weekly_report():
    """生成周报"""
    try:
        data = request.get_json() or {}
        week_start_str = data.get('week_start')
        
        week_start = None
        if week_start_str:
            week_start = datetime.fromisoformat(week_start_str.replace('Z', '+00:00'))
        
        report = ReportService.generate_weekly_report(current_user.id, week_start)
        
        return jsonify({
            'success': True,
            'message': '周报生成完成',
            'report': report.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"生成周报失败: {e}")
        return jsonify({'success': False, 'message': '生成周报失败'}), 500


@report_bp.route('/reports/monthly', methods=['POST'])
@login_required
def generate_monthly_report():
    """生成月报"""
    try:
        data = request.get_json() or {}
        year = data.get('year')
        month = data.get('month')
        
        report = ReportService.generate_monthly_report(current_user.id, year, month)
        
        return jsonify({
            'success': True,
            'message': '月报生成完成',
            'report': report.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"生成月报失败: {e}")
        return jsonify({'success': False, 'message': '生成月报失败'}), 500


@report_bp.route('/reports/<int:report_id>', methods=['GET'])
@login_required
def get_report(report_id):
    """获取报表详情"""
    try:
        report = ReportService.get_report(report_id, current_user.id)
        if not report:
            return jsonify({'success': False, 'message': '报表不存在'}), 404
        
        return jsonify({
            'success': True,
            'report': report.to_dict()
        })
        
    except Exception as e:
        logger.error(f"获取报表详情失败: {e}")
        return jsonify({'success': False, 'message': '获取报表详情失败'}), 500


@report_bp.route('/reports', methods=['GET'])
@login_required
def list_reports():
    """获取报表列表"""
    try:
        report_type = request.args.get('report_type')
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        result = ReportService.list_reports(
            user_id=current_user.id,
            report_type=report_type,
            status=status,
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'success': True,
            'reports': result['reports'],
            'pagination': {
                'total': result['total'],
                'page': result['page'],
                'per_page': result['per_page'],
                'pages': result['pages']
            }
        })
        
    except Exception as e:
        logger.error(f"获取报表列表失败: {e}")
        return jsonify({'success': False, 'message': '获取报表列表失败'}), 500


@report_bp.route('/reports/<int:report_id>', methods=['DELETE'])
@login_required
def delete_report(report_id):
    """删除报表"""
    try:
        ReportService.delete_report(report_id, current_user.id)
        
        return jsonify({
            'success': True,
            'message': '报表删除成功'
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"删除报表失败: {e}")
        return jsonify({'success': False, 'message': '删除报表失败'}), 500


# ========================================================================
# 报表定时任务管理
# ========================================================================

@report_bp.route('/schedules', methods=['POST'])
@login_required
def create_schedule():
    """创建报表定时任务"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        name = data.get('name')
        report_type = data.get('report_type')
        
        if not all([name, report_type]):
            return jsonify({'success': False, 'message': '缺少必填字段'}), 400
        
        schedule = ReportScheduleService.create_schedule(
            user_id=current_user.id,
            name=name,
            report_type=report_type,
            schedule_hour=data.get('schedule_hour', 0),
            schedule_day_of_week=data.get('schedule_day_of_week'),
            schedule_day_of_month=data.get('schedule_day_of_month'),
            notify_email=data.get('notify_email', False),
            notify_webhook=data.get('notify_webhook'),
        )
        
        return jsonify({
            'success': True,
            'message': '定时任务创建成功',
            'schedule': schedule.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"创建定时任务失败: {e}")
        return jsonify({'success': False, 'message': '创建定时任务失败'}), 500


@report_bp.route('/schedules/<int:schedule_id>', methods=['PUT'])
@login_required
def update_schedule(schedule_id):
    """更新报表定时任务"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '无效的请求数据'}), 400
        
        schedule = ReportScheduleService.update_schedule(
            schedule_id=schedule_id,
            user_id=current_user.id,
            **data
        )
        
        return jsonify({
            'success': True,
            'message': '定时任务更新成功',
            'schedule': schedule.to_dict()
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"更新定时任务失败: {e}")
        return jsonify({'success': False, 'message': '更新定时任务失败'}), 500


@report_bp.route('/schedules/<int:schedule_id>', methods=['DELETE'])
@login_required
def delete_schedule(schedule_id):
    """删除报表定时任务"""
    try:
        ReportScheduleService.delete_schedule(schedule_id, current_user.id)
        
        return jsonify({
            'success': True,
            'message': '定时任务删除成功'
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"删除定时任务失败: {e}")
        return jsonify({'success': False, 'message': '删除定时任务失败'}), 500


@report_bp.route('/schedules/<int:schedule_id>', methods=['GET'])
@login_required
def get_schedule(schedule_id):
    """获取报表定时任务详情"""
    try:
        schedule = ReportScheduleService.get_schedule(schedule_id, current_user.id)
        if not schedule:
            return jsonify({'success': False, 'message': '定时任务不存在'}), 404
        
        return jsonify({
            'success': True,
            'schedule': schedule.to_dict()
        })
        
    except Exception as e:
        logger.error(f"获取定时任务详情失败: {e}")
        return jsonify({'success': False, 'message': '获取定时任务详情失败'}), 500


@report_bp.route('/schedules', methods=['GET'])
@login_required
def list_schedules():
    """获取报表定时任务列表"""
    try:
        enabled = request.args.get('enabled')
        if enabled is not None:
            enabled = enabled.lower() == 'true'
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        result = ReportScheduleService.list_schedules(
            user_id=current_user.id,
            enabled=enabled,
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'success': True,
            'schedules': result['schedules'],
            'pagination': {
                'total': result['total'],
                'page': result['page'],
                'per_page': result['per_page'],
                'pages': result['pages']
            }
        })
        
    except Exception as e:
        logger.error(f"获取定时任务列表失败: {e}")
        return jsonify({'success': False, 'message': '获取定时任务列表失败'}), 500


@report_bp.route('/schedules/<int:schedule_id>/execute', methods=['POST'])
@login_required
def execute_schedule(schedule_id):
    """手动执行定时任务"""
    try:
        schedule = ReportScheduleService.get_schedule(schedule_id, current_user.id)
        if not schedule:
            return jsonify({'success': False, 'message': '定时任务不存在'}), 404
        
        report = ReportScheduleService.execute_schedule(schedule)
        
        return jsonify({
            'success': True,
            'message': '定时任务执行完成',
            'report': report.to_dict()
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"执行定时任务失败: {e}")
        return jsonify({'success': False, 'message': '执行定时任务失败'}), 500
