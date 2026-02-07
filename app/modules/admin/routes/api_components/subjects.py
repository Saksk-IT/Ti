# -*- coding: utf-8 -*-
"""Admin API routes - subjects management."""

import datetime
import io
import json
import os
import sqlite3
import zipfile

import pandas as pd
from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from app.core.extensions import limiter
from app.core.utils.database import get_db
from app.core.utils.cache_utils import bump_questions_version, bump_subjects_version
from app.core.utils.fill_blank_parser import parse_fill_blank
from app.core.utils.validators import parse_int, validate_password

from ..api_bp import admin_api_bp
from app.core.utils.decorators import subject_admin_required


@admin_api_bp.route('/subjects', methods=['GET'])
@subject_admin_required
def api_get_subjects():
    """获取科目列表（管理后台，包含锁定状态）"""
    conn = get_db()
    rows = conn.execute('''
        SELECT s.id, s.name, s.is_locked, COUNT(q.id) as question_count
        FROM subjects s
        LEFT JOIN questions q ON s.id = q.subject_id
        GROUP BY s.id, s.name, s.is_locked
        ORDER BY s.id
    ''').fetchall()
    
    subjects = [dict(row) for row in rows]
    return jsonify(subjects)



@admin_api_bp.route('/subjects', methods=['POST'])
@subject_admin_required
def api_add_subject():
    """添加科目"""
    data = request.json
    name = data.get('name')
    
    if not name:
        return jsonify({'status': 'error', 'message': '科目名不能为空'}), 400
    
    conn = get_db()
    try:
        conn.execute('INSERT INTO subjects (name) VALUES (?)', (name,))
        conn.commit()
        try:
            bump_subjects_version()
        except Exception:
            pass
        return jsonify({'status': 'success', 'message': '科目添加成功'})
    except sqlite3.IntegrityError as e:
        # 常见原因：该用户仍被其它表外键引用（例如聊天消息、通知、考试记录等）
        msg = str(e)
        if 'FOREIGN KEY constraint failed' in msg:
            return jsonify({'status': 'error', 'message': '删除失败：该用户仍有关联数据（外键约束），请先删除/转移其相关记录后再删除。'}), 400
        return jsonify({'status': 'error', 'message': msg}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/subjects/<int:subject_id>', methods=['PUT'])
@subject_admin_required
def api_edit_subject(subject_id):
    """编辑科目"""
    data = request.json
    name = data.get('name')
    
    if not name:
        return jsonify({'status': 'error', 'message': '科目名不能为空'}), 400
    
    conn = get_db()
    try:
        conn.execute('UPDATE subjects SET name=? WHERE id=?', (name, subject_id))
        conn.commit()
        try:
            bump_subjects_version()
        except Exception:
            pass
        return jsonify({'status': 'success', 'message': '科目修改成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/subjects/<int:subject_id>', methods=['DELETE'])
@subject_admin_required
def api_delete_subject(subject_id):
    """删除科目"""
    force = request.args.get('force') in ('1','true','yes')
    
    conn = get_db()
    try:
        qcount = conn.execute('SELECT COUNT(1) FROM questions WHERE subject_id=?', (subject_id,)).fetchone()[0]
        
        if qcount > 0 and not force:
            return jsonify({'status': 'error', 'message': f'该科目下仍有 {qcount} 道题，无法直接删除'}), 400
        
        if qcount > 0 and force:
            conn.execute('DELETE FROM favorites WHERE question_id IN (SELECT id FROM questions WHERE subject_id=?)', (subject_id,))
            conn.execute('DELETE FROM mistakes WHERE question_id IN (SELECT id FROM questions WHERE subject_id=?)', (subject_id,))
            conn.execute('DELETE FROM questions WHERE subject_id=?', (subject_id,))
        
        conn.execute('DELETE FROM subjects WHERE id=?', (subject_id,))
        conn.commit()
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
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/subjects/<int:subject_id>/lock', methods=['POST'])
@subject_admin_required
def api_lock_subject(subject_id):
    """锁定科目"""
    conn = get_db()
    try:
        # 检查科目是否存在
        subject = conn.execute('SELECT id, name FROM subjects WHERE id=?', (subject_id,)).fetchone()
        if not subject:
            return jsonify({'status': 'error', 'message': '科目不存在'}), 404
        
        conn.execute('UPDATE subjects SET is_locked=1 WHERE id=?', (subject_id,))
        conn.commit()
        try:
            bump_subjects_version()
        except Exception:
            pass
        
        return jsonify({'status': 'success', 'message': f'科目"{dict(subject)["name"]}"已锁定'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



@admin_api_bp.route('/subjects/<int:subject_id>/unlock', methods=['POST'])
@subject_admin_required
def api_unlock_subject(subject_id):
    """解锁科目"""
    conn = get_db()
    try:
        # 检查科目是否存在
        subject = conn.execute('SELECT id, name FROM subjects WHERE id=?', (subject_id,)).fetchone()
        if not subject:
            return jsonify({'status': 'error', 'message': '科目不存在'}), 404
        
        conn.execute('UPDATE subjects SET is_locked=0 WHERE id=?', (subject_id,))
        conn.commit()
        try:
            bump_subjects_version()
        except Exception:
            pass
        
        return jsonify({'status': 'success', 'message': f'科目"{dict(subject)["name"]}"已解锁'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


