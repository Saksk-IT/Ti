# -*- coding: utf-8 -*-

"""用户题库：题库管理 API"""

from flask import request, jsonify

from app.core.utils.database import get_db
from app.core.utils.decorators import auth_required, current_user_id

from .api_base import user_bank_api_bp, check_bank_access


@user_bank_api_bp.route('/list', methods=['GET'])
@auth_required
def get_banks():
    """获取我的题库列表"""
    user_id = current_user_id()
    category_id = request.args.get('category_id', type=int)
    is_public = request.args.get('is_public', type=int)

    conn = get_db()

    query = '''
        SELECT b.*, c.name as category_name
        FROM user_question_banks b
        LEFT JOIN user_bank_categories c ON b.category_id = c.id
        WHERE b.user_id = ? AND b.status = 1
    '''
    params = [user_id]

    if category_id is not None:
        query += ' AND b.category_id = ?'
        params.append(category_id)

    if is_public is not None:
        query += ' AND b.is_public = ?'
        params.append(is_public)

    query += ' ORDER BY b.updated_at DESC'

    banks = conn.execute(query, params).fetchall()

    return jsonify({
        'code': 0,
        'data': {
            'banks': [dict(b) for b in banks],
            'total': len(banks)
        }
    })


@user_bank_api_bp.route('/<int:bank_id>', methods=['GET'])
@auth_required
def get_bank_detail(bank_id):
    """获取题库详情"""
    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    conn = get_db()
    bank = conn.execute('''
        SELECT b.*, c.name as category_name, u.username as owner_username
        FROM user_question_banks b
        LEFT JOIN user_bank_categories c ON b.category_id = c.id
        LEFT JOIN users u ON b.user_id = u.id
        WHERE b.id = ?
    ''', (bank_id,)).fetchone()

    result = dict(bank)
    result['permission'] = permission
    result['access_type'] = access_type

    # 获取题库中的题型列表
    types_result = conn.execute('''
        SELECT DISTINCT type as p_type FROM user_bank_questions
        WHERE bank_id = ? AND type IS NOT NULL AND TRIM(type) != ''
        ORDER BY type
    ''', (bank_id,)).fetchall()
    from app.core.utils.portable_question_format import portable_type_to_q_type

    result['available_types'] = [
        portable_type_to_q_type((t['p_type'] or ''), essay_q_type='简答题')
        for t in (types_result or [])
        if t and t['p_type']
    ]

    return jsonify({
        'code': 0,
        'data': result
    })


@user_bank_api_bp.route('', methods=['POST'])
@auth_required
def create_bank():
    """创建题库"""
    user_id = current_user_id()
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()
    category_id = data.get('category_id')

    if not name:
        return jsonify({'code': 1, 'message': '题库名称不能为空'}), 400
    if len(name) < 2 or len(name) > 50:
        return jsonify({'code': 1, 'message': '题库名称需要2-50个字符'}), 400
    if description and len(description) > 200:
        return jsonify({'code': 1, 'message': '描述不能超过200个字符'}), 400

    conn = get_db()

    # 检查题库数量限制
    count = conn.execute(
        'SELECT COUNT(*) as cnt FROM user_question_banks WHERE user_id = ? AND status = 1',
        (user_id,)
    ).fetchone()['cnt']

    if count >= 20:
        return jsonify({'code': 1, 'message': '最多只能创建20个题库'}), 400

    # 检查分类是否存在
    if category_id:
        cat = conn.execute(
            'SELECT id FROM user_bank_categories WHERE id = ? AND user_id = ?',
            (category_id, user_id)
        ).fetchone()
        if not cat:
            return jsonify({'code': 1, 'message': '分类不存在'}), 400

    cursor = conn.execute(
        '''INSERT INTO user_question_banks (user_id, category_id, name, description)
           VALUES (?, ?, ?, ?)''',
        (user_id, category_id, name, description)
    )
    conn.commit()

    return jsonify({
        'code': 0,
        'data': {
            'id': cursor.lastrowid,
            'name': name
        }
    })


@user_bank_api_bp.route('/<int:bank_id>', methods=['PUT'])
@auth_required
def update_bank(bank_id):
    """编辑题库"""
    user_id = current_user_id()
    data = request.get_json() or {}

    conn = get_db()

    # 检查权限
    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    updates = []
    params = []

    if 'name' in data:
        name = (data['name'] or '').strip()
        if not name or len(name) < 2 or len(name) > 50:
            return jsonify({'code': 1, 'message': '题库名称需要2-50个字符'}), 400
        updates.append('name = ?')
        params.append(name)

    if 'description' in data:
        description = (data['description'] or '').strip()
        if description and len(description) > 200:
            return jsonify({'code': 1, 'message': '描述不能超过200个字符'}), 400
        updates.append('description = ?')
        params.append(description)

    if 'category_id' in data:
        category_id = data['category_id']
        if category_id:
            cat = conn.execute(
                'SELECT id FROM user_bank_categories WHERE id = ? AND user_id = ?',
                (category_id, user_id)
            ).fetchone()
            if not cat:
                return jsonify({'code': 1, 'message': '分类不存在'}), 400
        updates.append('category_id = ?')
        params.append(category_id)

    if not updates:
        return jsonify({'code': 1, 'message': '没有要更新的内容'}), 400

    updates.append('updated_at = CURRENT_TIMESTAMP')
    params.append(bank_id)

    conn.execute(
        f'UPDATE user_question_banks SET {", ".join(updates)} WHERE id = ?',
        params
    )
    conn.commit()

    return jsonify({'code': 0, 'message': '更新成功'})


@user_bank_api_bp.route('/<int:bank_id>', methods=['DELETE'])
@auth_required
def delete_bank(bank_id):
    """删除题库"""
    user_id = current_user_id()
    conn = get_db()

    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    # 软删除
    conn.execute(
        'UPDATE user_question_banks SET status = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (bank_id,)
    )
    conn.commit()

    return jsonify({'code': 0, 'message': '删除成功'})


@user_bank_api_bp.route('/<int:bank_id>/public', methods=['POST'])
@auth_required
def set_bank_public(bank_id):
    """设置题库公开状态"""
    user_id = current_user_id()
    data = request.get_json() or {}
    is_public = data.get('is_public', False)
    public_description = (data.get('public_description') or '').strip()

    conn = get_db()

    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    if is_public:
        conn.execute('''
            UPDATE user_question_banks
            SET is_public = 1, public_description = ?,
                public_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (public_description, bank_id))
        message = '题库已公开'
    else:
        conn.execute('''
            UPDATE user_question_banks
            SET is_public = 0, public_at = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (bank_id,))
        message = '题库已设为私密'

    conn.commit()

    return jsonify({'code': 0, 'message': message})
