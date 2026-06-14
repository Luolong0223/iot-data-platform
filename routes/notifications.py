"""消息通知中心路由 - 站内信/已读未读/批量通知"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc

from models.database import db, SystemMessage

logger = logging.getLogger(__name__)

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')


@notifications_bp.route('/inbox', methods=['GET'])
@login_required
def get_inbox():
    """获取用户收件箱"""
    page = request.args.get('page', 1, type=int)
    size = request.args.get('size', 20, type=int)
    is_read = request.args.get('is_read', type=lambda v: v.lower() == 'true' if v else None)
    
    query = SystemMessage.query.filter_by(user_id=current_user.id)
    
    if is_read is not None:
        query = query.filter_by(is_read=is_read)
    
    total = query.count()
    messages = query.order_by(desc(SystemMessage.created_at)).offset((page - 1) * size).limit(size).all()
    
    # 统计未读数
    unread_count = SystemMessage.query.filter_by(user_id=current_user.id, is_read=False).count()
    
    return jsonify({
        'success': True,
        'messages': [msg.to_dict() for msg in messages],
        'unread_count': unread_count,
        'pagination': {
            'page': page,
            'size': size,
            'total': total,
            'pages': (total + size - 1) // size
        }
    })


@notifications_bp.route('/<int:message_id>', methods=['GET'])
@login_required
def get_message(message_id):
    """获取单条消息详情"""
    message = SystemMessage.query.filter_by(id=message_id, user_id=current_user.id).first()
    if not message:
        return jsonify({'success': False, 'message': '消息不存在'}), 404
    
    # 自动标记为已读
    if not message.is_read:
        message.is_read = True
        message.read_at = datetime.utcnow()
        db.session.commit()
    
    return jsonify({'success': True, 'message': message.to_dict()})


@notifications_bp.route('/<int:message_id>/read', methods=['POST'])
@login_required
def mark_as_read(message_id):
    """标记消息为已读"""
    message = SystemMessage.query.filter_by(id=message_id, user_id=current_user.id).first()
    if not message:
        return jsonify({'success': False, 'message': '消息不存在'}), 404
    
    if not message.is_read:
        message.is_read = True
        message.read_at = datetime.utcnow()
        db.session.commit()
    
    return jsonify({'success': True, 'message': '已标记为已读'})


@notifications_bp.route('/batch/read', methods=['POST'])
@login_required
def batch_mark_as_read():
    """批量标记消息为已读"""
    data = request.get_json() or {}
    message_ids = data.get('message_ids', [])
    
    if not message_ids:
        # 标记所有未读为已读
        updated = SystemMessage.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).update({'is_read': True, 'read_at': datetime.utcnow()}, synchronize_session=False)
    else:
        updated = SystemMessage.query.filter(
            SystemMessage.id.in_(message_ids),
            SystemMessage.user_id == current_user.id,
            SystemMessage.is_read == False
        ).update({'is_read': True, 'read_at': datetime.utcnow()}, synchronize_session=False)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'已标记 {updated} 条消息为已读'
    })


@notifications_bp.route('/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    """删除消息"""
    message = SystemMessage.query.filter_by(id=message_id, user_id=current_user.id).first()
    if not message:
        return jsonify({'success': False, 'message': '消息不存在'}), 404
    
    db.session.delete(message)
    db.session.commit()
    
    return jsonify({'success': True, 'message': '消息已删除'})


@notifications_bp.route('/batch/delete', methods=['POST'])
@login_required
def batch_delete():
    """批量删除消息"""
    data = request.get_json() or {}
    message_ids = data.get('message_ids', [])
    
    if not message_ids:
        return jsonify({'success': False, 'message': '请选择要删除的消息'}), 400
    
    deleted = SystemMessage.query.filter(
        SystemMessage.id.in_(message_ids),
        SystemMessage.user_id == current_user.id
    ).delete(synchronize_session=False)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'已删除 {deleted} 条消息'
    })


@notifications_bp.route('/send', methods=['POST'])
@login_required
def send_notification():
    """发送通知（管理员或系统）"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': '无权发送通知'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '无效的请求数据'}), 400
    
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    level = data.get('type', 'info')
    target_user_ids = data.get('user_ids', [])  # 空表示所有用户
    
    if not title or not content:
        return jsonify({'success': False, 'message': '标题和内容不能为空'}), 400
    
    # 获取目标用户
    from models.database import User
    if target_user_ids:
        users = User.query.filter(User.id.in_(target_user_ids)).all()
    else:
        users = User.query.all()
    
    # 批量创建消息
    created_count = 0
    for user in users:
        msg = SystemMessage(
            user_id=user.id,
            title=title,
            content=content,
            level=level,
            is_read=False
        )
        db.session.add(msg)
        created_count += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'已发送 {created_count} 条通知'
    })


@notifications_bp.route('/unread-count', methods=['GET'])
@login_required
def get_unread_count():
    """获取未读消息数"""
    count = SystemMessage.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'success': True, 'unread_count': count})


@notifications_bp.route('/clear-read', methods=['POST'])
@login_required
def clear_read_messages():
    """清理已读消息"""
    deleted = SystemMessage.query.filter_by(
        user_id=current_user.id,
        is_read=True
    ).delete(synchronize_session=False)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'已清理 {deleted} 条已读消息'
    })
