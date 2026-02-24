# -*- coding: utf-8 -*-
"""Admin API routes - subjects management."""

from flask import (
    current_app,
    jsonify,
    request,
    session,
)

from app.core.extensions import db
from sqlalchemy import text
from app.core.utils.cache_utils import bump_questions_version, bump_subjects_version

from ..api_bp import admin_api_bp
from app.core.utils.decorators import subject_admin_required


@admin_api_bp.route('/subjects', methods=['GET'])
@subject_admin_required
def api_get_subjects():
    """获取科目列表（管理后台，包含锁定状态）"""
    rows = db.session.execute(text('''
        SELECT s.id, s.name, s.is_locked, COUNT(q.id) as question_count
        FROM subjects s
        LEFT JOIN questions q ON s.id = q.subject_id
        GROUP BY s.id, s.name, s.is_locked
        ORDER BY s.id
    ''')).fetchall()

    subjects = [dict(row._mapping) for row in rows]
    return jsonify(subjects)



@admin_api_bp.route('/subjects', methods=['POST'])
@subject_admin_required
def api_add_subject():
    """添加科目"""
    data = request.json
    name = data.get('name')
    
    if not name:
        return jsonify({'status': 'error', 'message': '科目名不能为空'}), 400
    
    try:
        db.session.execute(text('INSERT INTO subjects (name) VALUES (:name)'), {'name': name})
        db.session.commit()
        try:
            bump_subjects_version()
        except Exception:
            pass
        return jsonify({'status': 'success', 'message': '科目添加成功'})
    except Exception as e:
        db.session.rollback()
        msg = str(e)
        if 'foreign key' in msg.lower():
            return jsonify({'status': 'error', 'message': '删除失败：该用户仍有关联数据（外键约束），请先删除/转移其相关记录后再删除。'}), 400
        return jsonify({'status': 'error', 'message': msg}), 500



@admin_api_bp.route('/subjects/<int:subject_id>', methods=['PUT'])
@subject_admin_required
def api_edit_subject(subject_id):
    """编辑科目"""
    data = request.json
    name = data.get('name')
    
    if not name:
        return jsonify({'status': 'error', 'message': '科目名不能为空'}), 400
    
    try:
        db.session.execute(text('UPDATE subjects SET name=:name WHERE id=:sid'), {'name': name, 'sid': subject_id})
        db.session.commit()
        try:
            bump_subjects_version()
        except Exception:
            pass
        return jsonify({'status': 'success', 'message': '科目修改成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/subjects/<int:subject_id>', methods=['DELETE'])
@subject_admin_required
def api_delete_subject(subject_id):
    """删除科目"""
    force = request.args.get('force') in ('1','true','yes')
    
    try:
        qcount = db.session.execute(text('SELECT COUNT(1) FROM questions WHERE subject_id=:sid'), {'sid': subject_id}).scalar()

        if qcount > 0 and not force:
            return jsonify({'status': 'error', 'message': f'该科目下仍有 {qcount} 道题，无法直接删除'}), 400

        if qcount > 0 and force:
            db.session.execute(text('DELETE FROM favorites WHERE question_id IN (SELECT id FROM questions WHERE subject_id=:sid)'), {'sid': subject_id})
            db.session.execute(text('DELETE FROM mistakes WHERE question_id IN (SELECT id FROM questions WHERE subject_id=:sid)'), {'sid': subject_id})
            db.session.execute(text('DELETE FROM questions WHERE subject_id=:sid'), {'sid': subject_id})

        db.session.execute(text('DELETE FROM subjects WHERE id=:sid'), {'sid': subject_id})
        db.session.commit()
        try:
            bump_subjects_version()
        except Exception:
            pass
        if qcount > 0 and force:
            try:
                bump_questions_version()
            except Exception:
                pass

        return jsonify({'status': 'success', 'message': '科目删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/subjects/<int:subject_id>/lock', methods=['POST'])
@subject_admin_required
def api_lock_subject(subject_id):
    """锁定科目"""
    try:
        # 检查科目是否存在
        subject = db.session.execute(text('SELECT id, name FROM subjects WHERE id=:sid'), {'sid': subject_id}).fetchone()
        if not subject:
            return jsonify({'status': 'error', 'message': '科目不存在'}), 404

        db.session.execute(text('UPDATE subjects SET is_locked=true WHERE id=:sid'), {'sid': subject_id})
        db.session.commit()
        try:
            bump_subjects_version()
        except Exception:
            pass

        return jsonify({'status': 'success', 'message': f'科目"{subject._mapping["name"]}"已锁定'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/subjects/<int:subject_id>/unlock', methods=['POST'])
@subject_admin_required
def api_unlock_subject(subject_id):
    """解锁科目"""
    try:
        # 检查科目是否存在
        subject = db.session.execute(text('SELECT id, name FROM subjects WHERE id=:sid'), {'sid': subject_id}).fetchone()
        if not subject:
            return jsonify({'status': 'error', 'message': '科目不存在'}), 404

        db.session.execute(text('UPDATE subjects SET is_locked=false WHERE id=:sid'), {'sid': subject_id})
        db.session.commit()
        try:
            bump_subjects_version()
        except Exception:
            pass

        return jsonify({'status': 'success', 'message': f'科目"{subject._mapping["name"]}"已解锁'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


