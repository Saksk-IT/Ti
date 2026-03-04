# -*- coding: utf-8 -*-

"""用户题库：题库管理 API"""

from flask import request, jsonify
from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.api_response import success_response, error_response

from .api_base import user_bank_api_bp, check_bank_access


@user_bank_api_bp.route('/list', methods=['GET'])
@auth_required
def get_banks():
    """获取我的题库列表"""
    user_id = current_user_id()
    category_id = request.args.get('category_id', type=int)
    is_public = request.args.get('is_public', type=int)

    query = '''
        SELECT b.*, c.name as category_name
        FROM user_question_banks b
        LEFT JOIN user_bank_categories c ON b.category_id = c.id
        WHERE b.user_id = :user_id AND b.status = 1
    '''
    params: dict = {'user_id': user_id}

    if category_id is not None:
        query += ' AND b.category_id = :category_id'
        params['category_id'] = category_id

    if is_public is not None:
        query += ' AND b.is_public = :is_public'
        params['is_public'] = is_public

    query += ' ORDER BY b.updated_at DESC'

    banks = db.session.execute(text(query), params).fetchall()

    return success_response(data={
        'banks': [dict(b._mapping) for b in banks],
        'total': len(banks)
    })


@user_bank_api_bp.route('/<int:bank_id>', methods=['GET'])
@auth_required
def get_bank_detail(bank_id):
    """获取题库详情"""
    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return error_response('无权访问此题库', 403, code=403)

    bank = db.session.execute(text('''
        SELECT b.*, c.name as category_name, u.username as owner_username
        FROM user_question_banks b
        LEFT JOIN user_bank_categories c ON b.category_id = c.id
        LEFT JOIN users u ON b.user_id = u.id
        WHERE b.id = :bank_id
    '''), {'bank_id': bank_id}).fetchone()

    result = dict(bank._mapping)
    result['permission'] = permission
    result['access_type'] = access_type

    # 获取题库中的题型列表
    types_result = db.session.execute(text('''
        SELECT DISTINCT type as p_type FROM user_bank_questions
        WHERE bank_id = :bank_id AND type IS NOT NULL AND TRIM(type) != ''
        ORDER BY type
    '''), {'bank_id': bank_id}).fetchall()
    from app.core.utils.portable_question_format import portable_type_to_q_type

    result['available_types'] = [
        portable_type_to_q_type((t._mapping['p_type'] or ''), essay_q_type='简答题')
        for t in (types_result or [])
        if t and t._mapping['p_type']
    ]

    return success_response(data=result)


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
        return error_response('题库名称不能为空')
    if len(name) < 2 or len(name) > 50:
        return error_response('题库名称需要2-50个字符')
    if description and len(description) > 200:
        return error_response('描述不能超过200个字符')

    # 检查题库数量限制
    count = db.session.execute(
        text('SELECT COUNT(*) as cnt FROM user_question_banks WHERE user_id = :uid AND status = 1'),
        {'uid': user_id}
    ).fetchone()._mapping['cnt']

    if count >= 20:
        return error_response('最多只能创建20个题库')

    # 检查分类是否存在
    if category_id:
        cat = db.session.execute(
            text('SELECT id FROM user_bank_categories WHERE id = :cid AND user_id = :uid'),
            {'cid': category_id, 'uid': user_id}
        ).fetchone()
        if not cat:
            return error_response('分类不存在')

    result = db.session.execute(
        text('''INSERT INTO user_question_banks (user_id, category_id, name, description)
           VALUES (:user_id, :category_id, :name, :description)
           RETURNING id'''),
        {'user_id': user_id, 'category_id': category_id, 'name': name, 'description': description}
    )
    new_id = result.fetchone()[0]
    db.session.commit()

    return success_response(data={
        'id': new_id,
        'name': name
    })


@user_bank_api_bp.route('/<int:bank_id>', methods=['PUT'])
@auth_required
def update_bank(bank_id):
    """编辑题库"""
    user_id = current_user_id()
    data = request.get_json() or {}

    # 检查权限
    bank = db.session.execute(
        text('SELECT id FROM user_question_banks WHERE id = :bid AND user_id = :uid AND status = 1'),
        {'bid': bank_id, 'uid': user_id}
    ).fetchone()

    if not bank:
        return error_response('题库不存在或无权操作', 404)

    updates = []
    params: dict = {}

    if 'name' in data:
        name = (data['name'] or '').strip()
        if not name or len(name) < 2 or len(name) > 50:
            return error_response('题库名称需要2-50个字符')
        updates.append('name = :name')
        params['name'] = name

    if 'description' in data:
        description = (data['description'] or '').strip()
        if description and len(description) > 200:
            return error_response('描述不能超过200个字符')
        updates.append('description = :description')
        params['description'] = description

    if 'public_description' in data:
        public_description = (data['public_description'] or '').strip()
        if public_description and len(public_description) > 200:
            return error_response('公开描述不能超过200个字符')
        updates.append('public_description = :public_description')
        params['public_description'] = public_description

    if 'category_id' in data:
        category_id = data['category_id']
        if category_id:
            cat = db.session.execute(
                text('SELECT id FROM user_bank_categories WHERE id = :cid AND user_id = :uid'),
                {'cid': category_id, 'uid': user_id}
            ).fetchone()
            if not cat:
                return error_response('分类不存在')
        updates.append('category_id = :category_id')
        params['category_id'] = category_id

    if not updates:
        return error_response('没有要更新的内容')

    updates.append('updated_at = CURRENT_TIMESTAMP')
    params['bid'] = bank_id

    db.session.execute(
        text(f'UPDATE user_question_banks SET {", ".join(updates)} WHERE id = :bid'),
        params
    )
    db.session.commit()

    return success_response(message='更新成功')


@user_bank_api_bp.route('/<int:bank_id>', methods=['DELETE'])
@auth_required
def delete_bank(bank_id):
    """删除题库"""
    user_id = current_user_id()

    bank = db.session.execute(
        text('SELECT id FROM user_question_banks WHERE id = :bid AND user_id = :uid AND status = 1'),
        {'bid': bank_id, 'uid': user_id}
    ).fetchone()

    if not bank:
        return error_response('题库不存在或无权操作', 404)

    # 软删除
    db.session.execute(
        text('UPDATE user_question_banks SET status = 0, updated_at = CURRENT_TIMESTAMP WHERE id = :bid'),
        {'bid': bank_id}
    )
    db.session.commit()

    return success_response(message='删除成功')


@user_bank_api_bp.route('/<int:bank_id>/public', methods=['POST'])
@auth_required
def set_bank_public(bank_id):
    """设置题库公开状态"""
    user_id = current_user_id()
    data = request.get_json() or {}
    is_public = data.get('is_public', False)
    public_description = (data.get('public_description') or '').strip()

    bank = db.session.execute(
        text('SELECT id FROM user_question_banks WHERE id = :bid AND user_id = :uid AND status = 1'),
        {'bid': bank_id, 'uid': user_id}
    ).fetchone()

    if not bank:
        return error_response('题库不存在或无权操作', 404)

    if is_public:
        db.session.execute(text('''
            UPDATE user_question_banks
            SET is_public = true, public_description = :pdesc,
                public_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = :bid
        '''), {'pdesc': public_description, 'bid': bank_id})
        message = '题库已公开'
    else:
        db.session.execute(text('''
            UPDATE user_question_banks
            SET is_public = false, public_at = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE id = :bid
        '''), {'bid': bank_id})
        message = '题库已设为私密'

    db.session.commit()

    return success_response(message=message)
