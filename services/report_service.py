"""
数据聚合报表服务
Data Aggregation Report Service
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from models.database import db, Report, ReportSchedule, Device, DataPoint, AlarmRecord
from sqlalchemy import func, desc, and_

logger = logging.getLogger(__name__)


class ReportService:
    """报表服务"""
    
    @staticmethod
    def create_report(
        user_id: int,
        name: str,
        report_type: str,
        period_start: datetime,
        period_end: datetime,
    ) -> Report:
        """创建报表"""
        report = Report(
            user_id=user_id,
            name=name,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            status='pending'
        )
        
        db.session.add(report)
        db.session.commit()
        
        logger.info(f"创建报表: {report.id}, 类型: {report_type}")
        return report
    
    @staticmethod
    def generate_report(report_id: int, user_id: int) -> Report:
        """生成报表数据"""
        report = Report.query.filter_by(id=report_id, user_id=user_id).first()
        if not report:
            raise ValueError(f"报表不存在: {report_id}")
        
        if report.status == 'generating':
            raise ValueError("报表正在生成中")
        
        report.status = 'generating'
        db.session.commit()
        
        try:
            # 收集报表数据
            report_data = ReportService._collect_report_data(
                user_id, report.period_start, report.period_end
            )
            
            # 生成摘要
            summary = ReportService._generate_summary(report_data)
            
            report.report_data = json.dumps(report_data)
            report.summary = summary
            report.status = 'completed'
            report.completed_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"报表生成完成: {report.id}")
            return report
            
        except Exception as e:
            report.status = 'failed'
            report.error_message = str(e)
            db.session.commit()
            
            logger.error(f"报表生成失败: {report.id}, 错误: {e}")
            raise
    
    @staticmethod
    def _collect_report_data(user_id: int, start: datetime, end: datetime) -> Dict[str, Any]:
        """收集报表数据"""
        # 设备统计
        devices = Device.query.filter_by(user_id=user_id).all()
        device_count = len(devices)
        online_devices = sum(1 for d in devices if d.is_online)
        
        # 数据统计 (简化版 - 统计所有数据点)
        data_count = DataPoint.query.filter(
            DataPoint.timestamp >= start,
            DataPoint.timestamp <= end
        ).count()
        
        # 告警统计 (使用 user_id)
        alarms = AlarmRecord.query.filter(
            AlarmRecord.user_id == user_id,
            AlarmRecord.created_at >= start,
            AlarmRecord.created_at <= end
        ).all()
        
        alarm_count = len(alarms)
        alarm_by_level = {}
        for alarm in alarms:
            level = alarm.severity or 'warning'
            alarm_by_level[level] = alarm_by_level.get(level, 0) + 1
        
        # 按设备统计 (简化版)
        device_stats = []
        for device in devices[:10]:  # 只统计前10个设备
            device_stats.append({
                'device_id': device.id,
                'device_name': device.name,
                'is_online': device.is_online
            })
        
        # 按日期统计数据 (简化版)
        daily_stats = []
        current_date = start.date()
        end_date = end.date()
        
        while current_date <= end_date:
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())
            
            day_data_count = DataPoint.query.filter(
                DataPoint.timestamp >= day_start,
                DataPoint.timestamp <= day_end
            ).count()
            
            day_alarm_count = AlarmRecord.query.filter(
                AlarmRecord.user_id == user_id,
                AlarmRecord.created_at >= day_start,
                AlarmRecord.created_at <= day_end
            ).count()
            
            daily_stats.append({
                'date': current_date.isoformat(),
                'data_count': day_data_count,
                'alarm_count': day_alarm_count
            })
            
            current_date += timedelta(days=1)
        
        return {
            'period': {
                'start': start.isoformat(),
                'end': end.isoformat()
            },
            'overview': {
                'device_count': device_count,
                'online_devices': online_devices,
                'data_count': data_count,
                'alarm_count': alarm_count,
            },
            'alarm_by_level': alarm_by_level,
            'device_stats': device_stats,
            'daily_stats': daily_stats,
        }
    
    @staticmethod
    def _generate_summary(report_data: Dict[str, Any]) -> str:
        """生成报表摘要"""
        overview = report_data.get('overview', {})
        
        summary_parts = [
            f"设备总数: {overview.get('device_count', 0)}",
            f"在线设备: {overview.get('online_devices', 0)}",
            f"数据总量: {overview.get('data_count', 0)}",
            f"告警总数: {overview.get('alarm_count', 0)}",
        ]
        
        return "; ".join(summary_parts)
    
    @staticmethod
    def get_report(report_id: int, user_id: int) -> Optional[Report]:
        """获取报表详情"""
        return Report.query.filter_by(id=report_id, user_id=user_id).first()
    
    @staticmethod
    def list_reports(
        user_id: int,
        report_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """获取报表列表"""
        query = Report.query.filter_by(user_id=user_id)
        
        if report_type:
            query = query.filter_by(report_type=report_type)
        
        if status:
            query = query.filter_by(status=status)
        
        query = query.order_by(desc(Report.created_at))
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'reports': [r.to_dict() for r in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    
    @staticmethod
    def delete_report(report_id: int, user_id: int) -> bool:
        """删除报表"""
        report = Report.query.filter_by(id=report_id, user_id=user_id).first()
        if not report:
            raise ValueError(f"报表不存在: {report_id}")
        
        db.session.delete(report)
        db.session.commit()
        
        logger.info(f"删除报表: {report.id}")
        return True
    
    @staticmethod
    def generate_daily_report(user_id: int, date: Optional[datetime] = None) -> Report:
        """生成日报"""
        if date is None:
            date = datetime.utcnow() - timedelta(days=1)
        
        start = datetime.combine(date.date(), datetime.min.time())
        end = datetime.combine(date.date(), datetime.max.time())
        
        name = f"日报 - {date.strftime('%Y-%m-%d')}"
        
        report = ReportService.create_report(
            user_id=user_id,
            name=name,
            report_type='daily',
            period_start=start,
            period_end=end
        )
        
        return ReportService.generate_report(report.id, user_id)
    
    @staticmethod
    def generate_weekly_report(user_id: int, week_start: Optional[datetime] = None) -> Report:
        """生成周报"""
        if week_start is None:
            # 上周一
            today = datetime.utcnow().date()
            days_since_monday = today.weekday()
            week_start = datetime.combine(today - timedelta(days=days_since_monday + 7), datetime.min.time())
        
        start = week_start
        end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        name = f"周报 - {start.strftime('%Y-%m-%d')} 至 {end.strftime('%Y-%m-%d')}"
        
        report = ReportService.create_report(
            user_id=user_id,
            name=name,
            report_type='weekly',
            period_start=start,
            period_end=end
        )
        
        return ReportService.generate_report(report.id, user_id)
    
    @staticmethod
    def generate_monthly_report(user_id: int, year: Optional[int] = None, month: Optional[int] = None) -> Report:
        """生成月报"""
        if year is None or month is None:
            # 上个月
            today = datetime.utcnow().date()
            if today.month == 1:
                year = today.year - 1
                month = 12
            else:
                year = today.year
                month = today.month - 1
        
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        name = f"月报 - {year}年{month}月"
        
        report = ReportService.create_report(
            user_id=user_id,
            name=name,
            report_type='monthly',
            period_start=start,
            period_end=end
        )
        
        return ReportService.generate_report(report.id, user_id)


class ReportScheduleService:
    """报表定时任务服务"""
    
    @staticmethod
    def create_schedule(
        user_id: int,
        name: str,
        report_type: str,
        schedule_hour: int = 0,
        schedule_day_of_week: Optional[int] = None,
        schedule_day_of_month: Optional[int] = None,
        notify_email: bool = False,
        notify_webhook: Optional[str] = None,
    ) -> ReportSchedule:
        """创建定时任务"""
        schedule = ReportSchedule(
            user_id=user_id,
            name=name,
            report_type=report_type,
            schedule_hour=schedule_hour,
            schedule_day_of_week=schedule_day_of_week,
            schedule_day_of_month=schedule_day_of_month,
            notify_email=notify_email,
            notify_webhook=notify_webhook,
            enabled=True
        )
        
        # 计算下次执行时间
        schedule.next_run_at = ReportScheduleService._calculate_next_run(schedule)
        
        db.session.add(schedule)
        db.session.commit()
        
        logger.info(f"创建报表定时任务: {schedule.id}, 类型: {report_type}")
        return schedule
    
    @staticmethod
    def _calculate_next_run(schedule: ReportSchedule) -> datetime:
        """计算下次执行时间"""
        now = datetime.utcnow()
        
        if schedule.report_type == 'daily':
            next_run = now.replace(hour=schedule.schedule_hour, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
        
        elif schedule.report_type == 'weekly':
            days_until = (schedule.schedule_day_of_week - now.weekday()) % 7
            if days_until == 0 and now.hour >= schedule.schedule_hour:
                days_until = 7
            next_run = now.replace(hour=schedule.schedule_hour, minute=0, second=0, microsecond=0)
            next_run += timedelta(days=days_until)
        
        elif schedule.report_type == 'monthly':
            day = schedule.schedule_day_of_month or 1
            if now.day < day or (now.day == day and now.hour < schedule.schedule_hour):
                next_run = now.replace(day=day, hour=schedule.schedule_hour, minute=0, second=0, microsecond=0)
            else:
                # 下个月
                if now.month == 12:
                    next_run = now.replace(year=now.year + 1, month=1, day=day, hour=schedule.schedule_hour, minute=0, second=0, microsecond=0)
                else:
                    next_run = now.replace(month=now.month + 1, day=day, hour=schedule.schedule_hour, minute=0, second=0, microsecond=0)
        else:
            next_run = now + timedelta(days=1)
        
        return next_run
    
    @staticmethod
    def update_schedule(
        schedule_id: int,
        user_id: int,
        **kwargs
    ) -> ReportSchedule:
        """更新定时任务"""
        schedule = ReportSchedule.query.filter_by(id=schedule_id, user_id=user_id).first()
        if not schedule:
            raise ValueError(f"定时任务不存在: {schedule_id}")
        
        for key, value in kwargs.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)
        
        # 重新计算下次执行时间
        schedule.next_run_at = ReportScheduleService._calculate_next_run(schedule)
        
        db.session.commit()
        
        logger.info(f"更新报表定时任务: {schedule.id}")
        return schedule
    
    @staticmethod
    def delete_schedule(schedule_id: int, user_id: int) -> bool:
        """删除定时任务"""
        schedule = ReportSchedule.query.filter_by(id=schedule_id, user_id=user_id).first()
        if not schedule:
            raise ValueError(f"定时任务不存在: {schedule_id}")
        
        db.session.delete(schedule)
        db.session.commit()
        
        logger.info(f"删除报表定时任务: {schedule.id}")
        return True
    
    @staticmethod
    def get_schedule(schedule_id: int, user_id: int) -> Optional[ReportSchedule]:
        """获取定时任务详情"""
        return ReportSchedule.query.filter_by(id=schedule_id, user_id=user_id).first()
    
    @staticmethod
    def list_schedules(
        user_id: int,
        enabled: Optional[bool] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """获取定时任务列表"""
        query = ReportSchedule.query.filter_by(user_id=user_id)
        
        if enabled is not None:
            query = query.filter_by(enabled=enabled)
        
        query = query.order_by(ReportSchedule.next_run_at)
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'schedules': [s.to_dict() for s in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    
    @staticmethod
    def get_due_schedules() -> List[ReportSchedule]:
        """获取到期的定时任务"""
        now = datetime.utcnow()
        return ReportSchedule.query.filter(
            ReportSchedule.enabled == True,
            ReportSchedule.next_run_at <= now
        ).all()
    
    @staticmethod
    def execute_schedule(schedule: ReportSchedule) -> Report:
        """执行定时任务"""
        logger.info(f"执行报表定时任务: {schedule.id}")
        
        # 根据类型生成报表
        if schedule.report_type == 'daily':
            report = ReportService.generate_daily_report(schedule.user_id)
        elif schedule.report_type == 'weekly':
            report = ReportService.generate_weekly_report(schedule.user_id)
        elif schedule.report_type == 'monthly':
            report = ReportService.generate_monthly_report(schedule.user_id)
        else:
            raise ValueError(f"未知的报表类型: {schedule.report_type}")
        
        # 更新任务状态
        schedule.last_run_at = datetime.utcnow()
        schedule.next_run_at = ReportScheduleService._calculate_next_run(schedule)
        
        db.session.commit()
        
        # TODO: 发送通知
        if schedule.notify_email:
            logger.info(f"TODO: 发送报表邮件通知: {report.id}")
        
        if schedule.notify_webhook:
            logger.info(f"TODO: 发送报表 Webhook 通知: {report.id}")
        
        return report
