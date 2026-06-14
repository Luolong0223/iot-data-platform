"""
自定义大屏服务 (Custom Dashboard Service)
支持可拖拽布局的数据看板
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from models.database import db, DashboardLayout, DashboardWidget
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class DashboardService:
    """自定义大屏服务类"""

    @staticmethod
    def create_layout(user_id: int, name: str, **kwargs) -> Dict[str, Any]:
        """创建大屏布局"""
        try:
            layout = DashboardLayout(
                user_id=user_id,
                name=name,
                description=kwargs.get('description'),
                layout_config=json.dumps(kwargs.get('layout_config', []), ensure_ascii=False),
                is_default=kwargs.get('is_default', False),
                visibility=kwargs.get('visibility', 'private'),
                theme_config=json.dumps(kwargs.get('theme_config', {}), ensure_ascii=False)
            )
            db.session.add(layout)
            db.session.commit()
            logger.info(f"Created dashboard layout: {name} (id={layout.id})")
            return {'success': True, 'layout': layout.to_dict()}
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to create layout: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def update_layout(layout_id: int, user_id: int, **kwargs) -> Dict[str, Any]:
        """更新大屏布局"""
        try:
            layout = DashboardLayout.query.filter_by(id=layout_id, user_id=user_id).first()
            if not layout:
                return {'success': False, 'error': '大屏不存在'}
            
            if 'name' in kwargs:
                layout.name = kwargs['name']
            if 'description' in kwargs:
                layout.description = kwargs['description']
            if 'layout_config' in kwargs:
                layout.layout_config = json.dumps(kwargs['layout_config'], ensure_ascii=False)
            if 'is_default' in kwargs:
                layout.is_default = kwargs['is_default']
            if 'visibility' in kwargs:
                layout.visibility = kwargs['visibility']
            if 'theme_config' in kwargs:
                layout.theme_config = json.dumps(kwargs['theme_config'], ensure_ascii=False)
            
            db.session.commit()
            logger.info(f"Updated dashboard layout: {layout.name} (id={layout.id})")
            return {'success': True, 'layout': layout.to_dict()}
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to update layout: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def delete_layout(layout_id: int, user_id: int) -> Dict[str, Any]:
        """删除大屏布局"""
        try:
            layout = DashboardLayout.query.filter_by(id=layout_id, user_id=user_id).first()
            if not layout:
                return {'success': False, 'error': '大屏不存在'}
            
            db.session.delete(layout)
            db.session.commit()
            logger.info(f"Deleted dashboard layout: {layout.name} (id={layout.id})")
            return {'success': True, 'message': '大屏已删除'}
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to delete layout: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_layouts(user_id: int) -> List[Dict[str, Any]]:
        """获取用户的所有大屏布局"""
        layouts = DashboardLayout.query.filter_by(user_id=user_id)\
            .order_by(DashboardLayout.is_default.desc(), DashboardLayout.updated_at.desc()).all()
        return [l.to_dict() for l in layouts]

    @staticmethod
    def get_layout(layout_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """获取单个大屏布局"""
        layout = DashboardLayout.query.filter_by(id=layout_id, user_id=user_id).first()
        return layout.to_dict() if layout else None

    @staticmethod
    def add_widget(layout_id: int, user_id: int, widget_type: str, **kwargs) -> Dict[str, Any]:
        """添加组件到大屏"""
        try:
            layout = DashboardLayout.query.filter_by(id=layout_id, user_id=user_id).first()
            if not layout:
                return {'success': False, 'error': '大屏不存在'}
            
            widget = DashboardWidget(
                layout_id=layout_id,
                widget_type=widget_type,
                title=kwargs.get('title'),
                x=kwargs.get('x', 0),
                y=kwargs.get('y', 0),
                w=kwargs.get('w', 4),
                h=kwargs.get('h', 3),
                data_config=json.dumps(kwargs.get('data_config', {}), ensure_ascii=False),
                style_config=json.dumps(kwargs.get('style_config', {}), ensure_ascii=False),
                refresh_interval=kwargs.get('refresh_interval', 30),
                order=kwargs.get('order', 0)
            )
            db.session.add(widget)
            db.session.commit()
            logger.info(f"Added widget to layout {layout_id}: {widget_type} (id={widget.id})")
            return {'success': True, 'widget': widget.to_dict()}
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to add widget: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def update_widget(widget_id: int, user_id: int, **kwargs) -> Dict[str, Any]:
        """更新组件"""
        try:
            widget = DashboardWidget.query.join(DashboardLayout).filter(
                DashboardWidget.id == widget_id,
                DashboardLayout.user_id == user_id
            ).first()
            if not widget:
                return {'success': False, 'error': '组件不存在'}
            
            if 'title' in kwargs:
                widget.title = kwargs['title']
            if 'x' in kwargs:
                widget.x = kwargs['x']
            if 'y' in kwargs:
                widget.y = kwargs['y']
            if 'w' in kwargs:
                widget.w = kwargs['w']
            if 'h' in kwargs:
                widget.h = kwargs['h']
            if 'data_config' in kwargs:
                widget.data_config = json.dumps(kwargs['data_config'], ensure_ascii=False)
            if 'style_config' in kwargs:
                widget.style_config = json.dumps(kwargs['style_config'], ensure_ascii=False)
            if 'refresh_interval' in kwargs:
                widget.refresh_interval = kwargs['refresh_interval']
            if 'order' in kwargs:
                widget.order = kwargs['order']
            
            db.session.commit()
            logger.info(f"Updated widget: {widget.id}")
            return {'success': True, 'widget': widget.to_dict()}
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to update widget: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def delete_widget(widget_id: int, user_id: int) -> Dict[str, Any]:
        """删除组件"""
        try:
            widget = DashboardWidget.query.join(DashboardLayout).filter(
                DashboardWidget.id == widget_id,
                DashboardLayout.user_id == user_id
            ).first()
            if not widget:
                return {'success': False, 'error': '组件不存在'}
            
            db.session.delete(widget)
            db.session.commit()
            logger.info(f"Deleted widget: {widget.id}")
            return {'success': True, 'message': '组件已删除'}
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to delete widget: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def update_layout_positions(layout_id: int, user_id: int, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量更新组件位置（拖拽后保存）"""
        try:
            layout = DashboardLayout.query.filter_by(id=layout_id, user_id=user_id).first()
            if not layout:
                return {'success': False, 'error': '大屏不存在'}
            
            for pos in positions:
                widget = DashboardWidget.query.filter_by(
                    id=pos['id'],
                    layout_id=layout_id
                ).first()
                if widget:
                    widget.x = pos.get('x', widget.x)
                    widget.y = pos.get('y', widget.y)
                    widget.w = pos.get('w', widget.w)
                    widget.h = pos.get('h', widget.h)
            
            db.session.commit()
            logger.info(f"Updated positions for layout {layout_id}")
            return {'success': True, 'message': '位置已更新'}
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to update positions: {e}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def duplicate_layout(layout_id: int, user_id: int, new_name: str) -> Dict[str, Any]:
        """复制大屏布局"""
        try:
            original = DashboardLayout.query.filter_by(id=layout_id, user_id=user_id).first()
            if not original:
                return {'success': False, 'error': '大屏不存在'}
            
            # 创建新布局
            new_layout = DashboardLayout(
                user_id=user_id,
                name=new_name,
                description=original.description,
                layout_config=original.layout_config,
                is_default=False,
                visibility=original.visibility,
                theme_config=original.theme_config
            )
            db.session.add(new_layout)
            db.session.flush()
            
            # 复制所有组件
            for widget in original.widgets:
                new_widget = DashboardWidget(
                    layout_id=new_layout.id,
                    widget_type=widget.widget_type,
                    title=widget.title,
                    x=widget.x,
                    y=widget.y,
                    w=widget.w,
                    h=widget.h,
                    data_config=widget.data_config,
                    style_config=widget.style_config,
                    refresh_interval=widget.refresh_interval,
                    order=widget.order
                )
                db.session.add(new_widget)
            
            db.session.commit()
            logger.info(f"Duplicated layout {layout_id} to {new_layout.id}")
            return {'success': True, 'layout': new_layout.to_dict()}
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to duplicate layout: {e}")
            return {'success': False, 'error': str(e)}
