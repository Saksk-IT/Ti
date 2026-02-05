# -*- coding: utf-8 -*-
"""Admin API routes - coding question management."""

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
from app.core.utils.cache_utils import bump_questions_version
from app.core.utils.fill_blank_parser import parse_fill_blank
from app.core.utils.validators import parse_int, validate_password

from ..api_bp import admin_api_bp


@admin_api_bp.route('/coding/questions', methods=['GET'])
def api_get_coding_questions():
    """获取编程题列表"""
    try:
        conn = get_db()

        # 查询所有编程题（coding_questions 表）
        rows = conn.execute(
            '''
            SELECT
                cq.id,
                cq.coding_subject_id as subject_id,
                cq.title,
                cq.q_type,
                cq.description,
                cq.programming_language,
                cq.time_limit,
                cq.memory_limit,
                cq.code_template,
                cq.difficulty,
                cq.test_cases_json,
                cq.is_enabled,
                cq.created_at as updated_at,
                cs.name as subject_name
            FROM coding_questions cq
            LEFT JOIN coding_subjects cs ON cq.coding_subject_id = cs.id
            ORDER BY cq.id DESC
            '''
        ).fetchall()

        questions = []
        for row in (rows or []):
            q = dict(row)
            # 兼容旧字段名：content/explanation/tags
            q['content'] = q.get('title') or q.get('description') or ''
            q['explanation'] = q.get('description') or ''
            q['tags'] = []
            # 截断内容预览
            if q.get('content') and len(q['content']) > 100:
                q['content'] = q['content'][:100] + '...'
            questions.append(q)

        return jsonify({
            'status': 'success',
            'data': questions
        })
    except Exception as e:
        current_app.logger.error(f"获取编程题列表失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取编程题列表失败'
        }), 500



@admin_api_bp.route('/coding/questions', methods=['POST'])
def api_create_coding_question():
    """创建编程题"""
    try:
        data = request.get_json() or {}
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400

        subject_id = data.get('coding_subject_id') or data.get('subject_id')
        title = str(data.get('title') or data.get('content') or '').strip()
        description = str(data.get('description') or data.get('explanation') or '').strip()
        if not description and title:
            description = title

        # 验证必填字段
        if not subject_id or not title:
            return jsonify({'status': 'error', 'message': '科目和题目内容不能为空'}), 400
        
        uid = session.get('user_id')
        if not uid:
            return jsonify({
                'status': 'unauthorized',
                'message': '请先登录'
            }), 401
        
        conn = get_db()

        raw_diff = data.get('difficulty') or 'medium'
        diff_map = {'简单': 'easy', '中等': 'medium', '困难': 'hard'}
        difficulty = diff_map.get(str(raw_diff), str(raw_diff))
        if difficulty not in ('easy', 'medium', 'hard'):
            difficulty = 'medium'

        q_type = str(data.get('q_type') or '编程题').strip()
        if q_type not in ('函数题', '编程题'):
            q_type = '编程题'

        test_cases_json = data.get('test_cases_json')
        if not test_cases_json:
            test_cases_json = json.dumps({'test_cases': []}, ensure_ascii=False)
        elif isinstance(test_cases_json, (dict, list)):
            test_cases_json = json.dumps(test_cases_json, ensure_ascii=False)
        else:
            test_cases_json = str(test_cases_json)

        try:
            time_limit = int(data.get('time_limit') or 5)
        except Exception:
            time_limit = 5
        try:
            memory_limit = int(data.get('memory_limit') or 128)
        except Exception:
            memory_limit = 128
        is_enabled = 1 if bool(data.get('is_enabled', True)) else 0

        cursor = conn.execute(
            '''
            INSERT INTO coding_questions (
                coding_subject_id, title, q_type, description, difficulty,
                code_template, programming_language, time_limit, memory_limit,
                test_cases_json, is_enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                int(subject_id),
                title,
                q_type,
                description,
                difficulty,
                data.get('code_template', ''),
                data.get('programming_language', 'python'),
                time_limit,
                memory_limit,
                test_cases_json,
                is_enabled,
            ),
        )
        conn.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
        
        return jsonify({
            'status': 'success',
            'message': '编程题创建成功',
            'data': {'id': cursor.lastrowid}
        }), 201
        
    except sqlite3.IntegrityError as e:
        conn.rollback()
        return jsonify({
            'status': 'error',
            'message': '数据已存在或违反约束'
        }), 400
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"创建编程题失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '创建编程题失败'
        }), 500



@admin_api_bp.route('/coding/questions/<int:question_id>', methods=['PUT'])
def api_update_coding_question(question_id):
    """更新编程题"""
    try:
        data = request.get_json() or {}
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        uid = session.get('user_id')
        if not uid:
            return jsonify({
                'status': 'unauthorized',
                'message': '请先登录'
            }), 401
        
        conn = get_db()

        row = conn.execute(
            'SELECT * FROM coding_questions WHERE id = ?',
            (int(question_id),),
        ).fetchone()
        if not row:
            return jsonify({'status': 'error', 'message': '题目不存在'}), 404

        cur = dict(row)

        subject_id = data.get('coding_subject_id') or data.get('subject_id') or cur.get('coding_subject_id')
        title = data.get('title') if 'title' in data else (data.get('content') if 'content' in data else cur.get('title'))
        title = str(title or '').strip()
        description = data.get('description') if 'description' in data else (data.get('explanation') if 'explanation' in data else cur.get('description'))
        description = str(description or '').strip()
        if not description and title:
            description = title

        raw_diff = data.get('difficulty') if 'difficulty' in data else cur.get('difficulty')
        diff_map = {'简单': 'easy', '中等': 'medium', '困难': 'hard'}
        difficulty = diff_map.get(str(raw_diff), str(raw_diff))
        if difficulty not in ('easy', 'medium', 'hard'):
            difficulty = 'medium'

        q_type = data.get('q_type') if 'q_type' in data else cur.get('q_type')
        q_type = str(q_type or '').strip()
        if q_type not in ('函数题', '编程题'):
            q_type = '编程题'

        programming_language = data.get('programming_language') if 'programming_language' in data else cur.get('programming_language', 'python')
        code_template = data.get('code_template') if 'code_template' in data else cur.get('code_template', '')

        try:
            time_limit = int(data.get('time_limit')) if 'time_limit' in data else int(cur.get('time_limit') or 5)
        except Exception:
            time_limit = int(cur.get('time_limit') or 5)
        try:
            memory_limit = int(data.get('memory_limit')) if 'memory_limit' in data else int(cur.get('memory_limit') or 128)
        except Exception:
            memory_limit = int(cur.get('memory_limit') or 128)

        test_cases_json = data.get('test_cases_json') if 'test_cases_json' in data else cur.get('test_cases_json')
        if not test_cases_json:
            test_cases_json = json.dumps({'test_cases': []}, ensure_ascii=False)
        elif isinstance(test_cases_json, (dict, list)):
            test_cases_json = json.dumps(test_cases_json, ensure_ascii=False)
        else:
            test_cases_json = str(test_cases_json)

        is_enabled = data.get('is_enabled') if 'is_enabled' in data else cur.get('is_enabled', 1)
        is_enabled = 1 if bool(is_enabled) else 0

        conn.execute(
            '''
            UPDATE coding_questions SET
                coding_subject_id = ?,
                title = ?,
                q_type = ?,
                description = ?,
                difficulty = ?,
                programming_language = ?,
                code_template = ?,
                time_limit = ?,
                memory_limit = ?,
                test_cases_json = ?,
                is_enabled = ?
            WHERE id = ?
            ''',
            (
                int(subject_id) if subject_id is not None and str(subject_id).strip() else None,
                title,
                q_type,
                description,
                difficulty,
                str(programming_language or 'python'),
                str(code_template or ''),
                time_limit,
                memory_limit,
                test_cases_json,
                is_enabled,
                int(question_id),
            ),
        )
        conn.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
        
        return jsonify({
            'status': 'success',
            'message': '编程题更新成功'
        })
        
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"更新编程题失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '更新编程题失败'
        }), 500



@admin_api_bp.route('/coding/questions/<int:question_id>', methods=['DELETE'])
def api_delete_coding_question(question_id):
    """删除编程题"""
    try:
        uid = session.get('user_id')
        if not uid:
            return jsonify({
                'status': 'unauthorized',
                'message': '请先登录'
            }), 401
        
        conn = get_db()

        row = conn.execute(
            'SELECT id FROM coding_questions WHERE id = ?',
            (int(question_id),),
        ).fetchone()
        if not row:
            return jsonify({'status': 'error', 'message': '题目不存在'}), 404

        # 删除编程题
        conn.execute('DELETE FROM coding_questions WHERE id = ?', (int(question_id),))
        conn.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
        
        return jsonify({
            'status': 'success',
            'message': '编程题删除成功'
        })
        
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"删除编程题失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '删除编程题失败'
        }), 500



