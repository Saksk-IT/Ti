# -*- coding: utf-8 -*-

"""用户题库：分类管理 API"""

from flask import request, jsonify
from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.decorators import auth_required, current_user_id

from .api_base import user_bank_api_bp


@user_bank_api_bp.route('/categories', methods=['GET'])
@auth_required
def get_categories():
    """获取分类列表"""
    user_id = current_user_id()

    categories = db.session.execute(text('''
        SELECT c.*,
               (SELECT COUNT(*) FROM user_question_banks WHERE category_id = c.id AND status = 1) as bank_count
        FROM user_bank_categories c
        WHERE c.user_id = :user_id
        ORDER BY c.sort_order ASC, c.id ASC
    '''), {'user_id': user_id}).fetchall()

    return jsonify({
        'code': 0,
        'data': {
            'categories': [dict(c._mapping) for c in categories]
        }
    })


@user_bank_api_bp.route('/categories', methods=['POST'])
@auth_required
def create_category():
    """创建分类"""
    user_id = current_user_id()
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()

    if not name:
        return jsonify({'code': 1, 'message': '分类名称不能为空'}), 400
    if len(name) > 50:
        return jsonify({'code': 1, 'message': '分类名称不能超过50个字符'}), 400

    # 检查分类数量限制
    count = db.session.execute(
        text('SELECT COUNT(*) as cnt FROM user_bank_categories WHERE user_id = :user_id'),
        {'user_id': user_id}
    ).fetchone()._mapping['cnt']

    if count >= 10:
        return jsonify({'code': 1, 'message': '最多只能创建10个分类'}), 400

    # 检查重复
    existing = db.session.execute(
        text('SELECT id FROM user_bank_categories WHERE user_id = :user_id AND name = :name'),
        {'user_id': user_id, 'name': name}
    ).fetchone()

    if existing:
        return jsonify({'code': 1, 'message': '分类名称已存在'}), 400

    result = db.session.execute(
        text('''INSERT INTO user_bank_categories (user_id, name, description, sort_order)
           VALUES (:user_id, :name, :description,
                   (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_categories WHERE user_id = :user_id2))'''),
        {'user_id': user_id, 'name': name, 'description': description, 'user_id2': user_id}
    )
    db.session.commit()

    return jsonify({
        'code': 0,
        'data': {
            'id': result.lastrowid,
            'name': name
        }
    })


@user_bank_api_bp.route('/categories/<int:category_id>', methods=['PUT'])
@auth_required
def update_category(category_id):
    """编辑分类"""
    user_id = current_user_id()
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()

    if not name:
        return jsonify({'code': 1, 'message': '分类名称不能为空'}), 400

    # 检查分类是否存在且属于当前用户
    cat = db.session.execute(
        text('SELECT id FROM user_bank_categories WHERE id = :cat_id AND user_id = :user_id'),
        {'cat_id': category_id, 'user_id': user_id}
    ).fetchone()

    if not cat:
        return jsonify({'code': 1, 'message': '分类不存在'}), 404

    # 检查重复
    existing = db.session.execute(
        text('SELECT id FROM user_bank_categories WHERE user_id = :user_id AND name = :name AND id != :cat_id'),
        {'user_id': user_id, 'name': name, 'cat_id': category_id}
    ).fetchone()

    if existing:
        return jsonify({'code': 1, 'message': '分类名称已存在'}), 400

    db.session.execute(
        text('''UPDATE user_bank_categories SET name = :name, description = :description, updated_at = CURRENT_TIMESTAMP
           WHERE id = :cat_id AND user_id = :user_id'''),
        {'name': name, 'description': description, 'cat_id': category_id, 'user_id': user_id}
    )
    db.session.commit()

    return jsonify({'code': 0, 'message': '更新成功'})


@user_bank_api_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@auth_required
def delete_category(category_id):
    """删除分类"""
    user_id = current_user_id()

    # 检查分类是否存在
    cat = db.session.execute(
        text('SELECT id FROM user_bank_categories WHERE id = :cat_id AND user_id = :user_id'),
        {'cat_id': category_id, 'user_id': user_id}
    ).fetchone()

    if not cat:
        return jsonify({'code': 1, 'message': '分类不存在'}), 404

    # 检查是否有题库使用此分类
    bank_count = db.session.execute(
        text('SELECT COUNT(*) as cnt FROM user_question_banks WHERE category_id = :cat_id AND status = 1'),
        {'cat_id': category_id}
    ).fetchone()._mapping['cnt']

    if bank_count > 0:
        return jsonify({'code': 1, 'message': f'该分类下还有{bank_count}个题库，请先移除'}), 400

    db.session.execute(
        text('DELETE FROM user_bank_categories WHERE id = :cat_id'),
        {'cat_id': category_id}
    )
    db.session.commit()

    return jsonify({'code': 0, 'message': '删除成功'})
