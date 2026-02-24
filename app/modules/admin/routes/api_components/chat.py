# -*- coding: utf-8 -*-
"""Admin API routes - chat management."""

from flask import (
    current_app,
    jsonify,
    request,
    session,
)

from app.core.extensions import db
from sqlalchemy import text

from ..api_bp import admin_api_bp
from app.core.utils.decorators import admin_required


@admin_api_bp.route('/chat/stats', methods=['GET'])
@admin_required
def api_chat_stats():
    """获取聊天统计数据"""
    try:
        # 会话总数
        conv_count = db.session.execute(text('SELECT COUNT(*) FROM chat_conversations')).scalar()

        # 消息总数
        msg_count = db.session.execute(text('SELECT COUNT(*) FROM chat_messages')).scalar()

        # 今日消息数
        today_msg_count = db.session.execute(text('''
            SELECT COUNT(*) FROM chat_messages
            WHERE DATE(created_at AT TIME ZONE 'Asia/Shanghai') = DATE(NOW() AT TIME ZONE 'Asia/Shanghai')
        ''')).scalar()

        # 活跃会话数（最近7天有消息的会话）
        active_conv_count = db.session.execute(text('''
            SELECT COUNT(DISTINCT conversation_id) FROM chat_messages
            WHERE created_at >= (NOW() AT TIME ZONE 'Asia/Shanghai' - INTERVAL '7 days')
        ''')).scalar()

        # 私聊会话数
        direct_conv_count = db.session.execute(
            text('SELECT COUNT(*) FROM chat_conversations WHERE c_type = :ctype'),
            {'ctype': 'direct'}
        ).scalar()
        
        return jsonify({
            'status': 'success',
            'data': {
                'conv_count': conv_count,
                'msg_count': msg_count,
                'today_msg_count': today_msg_count,
                'active_conv_count': active_conv_count,
                'direct_conv_count': direct_conv_count
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取聊天统计失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取统计数据失败'
        }), 500



@admin_api_bp.route('/chat/conversations', methods=['GET'])
@admin_required
def api_chat_conversations():
    """获取会话列表（支持分页和搜索）"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        keyword = request.args.get('keyword', '').strip()
        offset = (page - 1) * per_page
        
        # 构建基础查询
        base_sql = '''
            SELECT
                c.id,
                c.c_type,
                c.title,
                c.direct_pair_key,
                c.created_at,
                c.updated_at,
                (SELECT COUNT(DISTINCT user_id) FROM chat_members WHERE conversation_id = c.id) as member_count,
                (SELECT COUNT(*) FROM chat_messages WHERE conversation_id = c.id) as message_count,
                (SELECT MAX(id) FROM chat_messages WHERE conversation_id = c.id) as last_message_id,
                (SELECT MAX(created_at) FROM chat_messages WHERE conversation_id = c.id) as last_message_time
            FROM chat_conversations c
        '''

        where_clause = ''
        params = {}

        if keyword:
            where_clause = ' WHERE c.title LIKE :keyword'
            params['keyword'] = f'%{keyword}%'

        # 获取总数
        count_sql = f'SELECT COUNT(*) FROM chat_conversations c{where_clause}'
        total = db.session.execute(text(count_sql), params).scalar()

        # 获取分页数据
        data_sql = f'{base_sql}{where_clause} ORDER BY c.updated_at DESC LIMIT :limit OFFSET :offset'
        params['limit'] = per_page
        params['offset'] = offset
        rows = db.session.execute(text(data_sql), params).fetchall()

        conversations = []
        for row in rows:
            conv = dict(row._mapping)

            # 对于direct会话，获取参与用户信息
            if conv['c_type'] == 'direct' and conv['direct_pair_key']:
                try:
                    parts = conv['direct_pair_key'].split(':')
                    if len(parts) == 2:
                        uid1, uid2 = int(parts[0]), int(parts[1])
                        users = db.session.execute(text('''
                            SELECT id, username, avatar
                            FROM users
                            WHERE id IN (:uid1, :uid2)
                        '''), {'uid1': uid1, 'uid2': uid2}).fetchall()
                        conv['members'] = [dict(u._mapping) for u in users]
                except (ValueError, IndexError):
                    pass
            
            conversations.append(conv)
        
        return jsonify({
            'status': 'success',
            'data': {
                'conversations': conversations,
                'total': total,
                'page': page,
                'per_page': per_page
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取会话列表失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取会话列表失败'
        }), 500



@admin_api_bp.route('/chat/conversations/<int:conversation_id>/messages', methods=['GET'])
@admin_required
def api_chat_conversation_messages(conversation_id: int):
    """获取会话消息列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        offset = (page - 1) * per_page
        
        # 验证会话是否存在
        conv = db.session.execute(
            text('SELECT id FROM chat_conversations WHERE id = :cid'),
            {'cid': conversation_id}
        ).fetchone()
        if not conv:
            return jsonify({
                'status': 'error',
                'message': '会话不存在'
            }), 404

        # 获取消息列表
        messages = db.session.execute(text('''
            SELECT
                m.id,
                m.conversation_id,
                m.sender_id,
                u.username as sender_username,
                u.avatar as sender_avatar,
                m.content,
                m.content_type,
                m.created_at
            FROM chat_messages m
            LEFT JOIN users u ON m.sender_id = u.id
            WHERE m.conversation_id = :cid
            ORDER BY m.id DESC
            LIMIT :limit OFFSET :offset
        '''), {'cid': conversation_id, 'limit': per_page, 'offset': offset}).fetchall()

        # 获取总数
        total = db.session.execute(
            text('SELECT COUNT(*) FROM chat_messages WHERE conversation_id = :cid'),
            {'cid': conversation_id}
        ).scalar()
        
        return jsonify({
            'status': 'success',
            'data': {
                'messages': [dict(msg._mapping) for msg in messages],
                'total': total,
                'page': page,
                'per_page': per_page
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取会话消息失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取消息列表失败'
        }), 500



@admin_api_bp.route('/chat/conversations/<int:conversation_id>', methods=['DELETE'])
@admin_required
def api_delete_conversation(conversation_id: int):
    """删除会话（级联删除相关消息和成员）"""
    try:
        # 验证会话是否存在
        conv = db.session.execute(
            text('SELECT id FROM chat_conversations WHERE id = :cid'),
            {'cid': conversation_id}
        ).fetchone()
        if not conv:
            return jsonify({
                'status': 'error',
                'message': '会话不存在'
            }), 404

        # 删除会话（由于外键约束，会自动删除相关消息和成员）
        db.session.execute(text('DELETE FROM chat_conversations WHERE id = :cid'), {'cid': conversation_id})
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': '会话已删除'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除会话失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '删除会话失败'
        }), 500



@admin_api_bp.route('/chat/messages/<int:message_id>', methods=['DELETE'])
@admin_required
def api_delete_message(message_id: int):
    """删除消息"""
    try:
        # 验证消息是否存在
        msg = db.session.execute(
            text('SELECT id FROM chat_messages WHERE id = :mid'),
            {'mid': message_id}
        ).fetchone()
        if not msg:
            return jsonify({
                'status': 'error',
                'message': '消息不存在'
            }), 404

        # 删除消息
        db.session.execute(text('DELETE FROM chat_messages WHERE id = :mid'), {'mid': message_id})
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': '消息已删除'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除消息失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '删除消息失败'
        }), 500

