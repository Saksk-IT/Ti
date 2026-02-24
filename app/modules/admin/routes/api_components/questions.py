# -*- coding: utf-8 -*-
"""Admin API routes - questions/types management."""

import datetime
import io
import json
import os
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

from app.core.extensions import db, limiter
from sqlalchemy import text
from app.core.utils.cache_utils import bump_questions_version
from app.core.utils.fill_blank_parser import parse_fill_blank
from app.core.utils.validators import parse_int, validate_password

from ..api_bp import admin_api_bp
from app.core.utils.decorators import subject_admin_required


@admin_api_bp.route('/types', methods=['GET'])
@subject_admin_required
def get_question_types():
    """获取题型列表"""
    from app.core.utils.portable_question_format import portable_type_to_q_type

    rows = db.session.execute(text('SELECT DISTINCT type AS p_type FROM questions')).fetchall()
    out = []
    for r in rows or []:
        try:
            pt = (r._mapping['p_type'] if r and r._mapping['p_type'] is not None else '').strip()
        except Exception:
            pt = ''
        if not pt:
            continue
        out.append(portable_type_to_q_type(pt))
    return jsonify(sorted(list(set(out))))



@admin_api_bp.route('/questions', methods=['GET'])
@subject_admin_required
def get_filtered_questions():
    """获取筛选后的题目列表"""
    from app.core.utils.portable_question_format import any_type_to_portable_type, portable_question_to_internal, tags_to_storage_str

    subject_id = request.args.get('subject_id')
    q_type = request.args.get('type', 'all')
    
    conn_params = {}

    sql = '''
        SELECT q.id, q.subject_id, q.type, q.content, q.difficulty, q.tags, q.image_path, u.username as created_by, q.updated_at
        FROM questions q
        LEFT JOIN users u ON q.created_by = u.id
        WHERE 1=1
    '''

    if subject_id:
        sql += ' AND q.subject_id = :subject_id'
        conn_params['subject_id'] = subject_id

    if q_type != 'all':
        sql += ' AND q.type = :q_type'
        conn_params['q_type'] = any_type_to_portable_type(q_type)

    sql += ' ORDER BY q.id DESC'

    rows = db.session.execute(text(sql), conn_params).fetchall()
    questions = []
    for row in rows:
        question_dict = dict(row._mapping)
        # PQF -> 兼容字段（q_type/content 填空 __）
        try:
            portable = {
                "id": int(question_dict.get("id") or 0),
                "type": question_dict.get("type") or "",
                "content": question_dict.get("content") or "",
                "options": [],
                "answer": [],
                "analysis": "",
                "tags": [],
                "difficulty": question_dict.get("difficulty") if question_dict.get("difficulty") is not None else 1,
            }
            internal, _errors = portable_question_to_internal(portable, scope="question_center")
            question_dict["q_type"] = internal.get("q_type") or ""
            question_dict["content"] = internal.get("content") or question_dict.get("content") or ""
        except Exception:
            question_dict["q_type"] = ''

        # tags：DB 存 JSON 数组；管理页继续用逗号字符串
        try:
            raw_tags = question_dict.get('tags')
            tags_list = json.loads(raw_tags) if isinstance(raw_tags, str) and raw_tags.strip().startswith('[') else raw_tags
            question_dict['tags'] = tags_to_storage_str(tags_list)
        except Exception:
            # 兜底：保持原值或空
            question_dict['tags'] = (question_dict.get('tags') or '')

        image_path = question_dict.get('image_path')
        # Compatibility: if it's a non-empty string and not a JSON array, wrap it
        if image_path and isinstance(image_path, str) and not image_path.strip().startswith('['):
            question_dict['image_path'] = json.dumps([image_path])
        # If it's an empty string or None, make it an empty JSON array
        elif not image_path:
             question_dict['image_path'] = '[]'
        questions.append(question_dict)
    
    return jsonify(questions)



@admin_api_bp.route('/questions/<int:question_id>', methods=['GET'])
@subject_admin_required
def get_single_question(question_id):
    """获取单个题目"""
    from app.core.utils.portable_question_format import portable_question_to_internal, tags_to_storage_str

    row = db.session.execute(text('SELECT * FROM questions WHERE id=:qid'), {'qid': question_id}).fetchone()

    if row:
        question_dict = dict(row._mapping)

        # PQF -> 兼容字段（q_type/答案字符串/解析/填空 __）
        try:
            portable = {
                "id": int(question_dict.get("id") or 0),
                "type": question_dict.get("type") or "",
                "content": question_dict.get("content") or "",
                "options": json.loads(question_dict.get("options") or "[]"),
                "answer": json.loads(question_dict.get("answer") or "[]"),
                "analysis": question_dict.get("analysis") or "",
                "tags": json.loads(question_dict.get("tags") or "[]"),
                "difficulty": question_dict.get("difficulty") if question_dict.get("difficulty") is not None else 1,
            }
            internal, _errors = portable_question_to_internal(portable, scope="question_center")
            question_dict["q_type"] = internal.get("q_type") or ""
            question_dict["content"] = internal.get("content") or question_dict.get("content") or ""
            question_dict["answer"] = internal.get("answer") or ""
            question_dict["explanation"] = internal.get("explanation") or ""
        except Exception:
            question_dict["q_type"] = question_dict.get("q_type") or ""
            question_dict["answer"] = ""
            question_dict["explanation"] = ""

        # tags：管理页使用逗号分隔字符串
        try:
            question_dict["tags"] = tags_to_storage_str(json.loads(question_dict.get("tags") or "[]"))
        except Exception:
            question_dict["tags"] = question_dict.get("tags") or ""

        image_path = question_dict.get('image_path')
        # Compatibility: if it's a non-empty string and not a JSON array, wrap it
        if image_path and isinstance(image_path, str) and not image_path.strip().startswith('['):
            question_dict['image_path'] = json.dumps([image_path])
        # If it's an empty string or None, make it an empty JSON array
        elif not image_path:
             question_dict['image_path'] = '[]'
        return jsonify(question_dict)
    return jsonify({'error': 'not found'}), 404



@admin_api_bp.route('/questions', methods=['POST'])
@subject_admin_required
def add_question():
    """添加题目"""
    data = request.json
    uid = session.get('user_id')
    
    try:
        from app.core.utils.portable_question_format import internal_question_to_portable

        q_type = data.get('q_type')
        answer = (data.get('answer') or '').strip()
        options_str = data.get('options', '[]')
        
        # 多选题验证：确保答案至少有两个选项
        if q_type == '多选题':
            if len(answer) < 2:
                return jsonify({'status':'error','message':'多选题答案至少需要两个选项，例如：AB 或 ABC'}), 400
            # 验证答案中的所有字母是否在选项范围内
            try:
                options_list = json.loads(options_str) if isinstance(options_str, str) else options_str
                if isinstance(options_list, list) and len(options_list) > 0:
                    from app.core.utils.options_parser import parse_options
                    parsed_options = parse_options(options_list)
                    valid_keys = {opt['key'] for opt in parsed_options if opt.get('key')}
                    answer_keys = set(answer.upper())
                    invalid_keys = answer_keys - valid_keys
                    if invalid_keys:
                        return jsonify({'status':'error','message':f'多选题答案中包含无效选项：{", ".join(sorted(invalid_keys))}。有效选项为：{", ".join(sorted(valid_keys))}'}), 400
            except Exception:
                pass  # 如果解析选项失败，跳过验证
        
        portable = internal_question_to_portable(
            q_id=None,
            q_type=q_type,
            content=data.get('content'),
            options=options_str,
            answer=answer,
            explanation=data.get('explanation', ''),
            difficulty=data.get('difficulty', 1),
            tags=data.get('tags'),
        )

        result = db.session.execute(
            text('''
            INSERT INTO questions
            (subject_id, type, content, options, answer, analysis, difficulty, tags, image_path, created_by, updated_at)
            VALUES (:subject_id, :type, :content, :options, :answer, :analysis, :difficulty, :tags, :image_path, :created_by, CURRENT_TIMESTAMP)
            RETURNING id
            '''),
            {
                'subject_id': data.get('subject_id'),
                'type': portable.get('type') or 'essay',
                'content': portable.get('content') or '',
                'options': json.dumps(portable.get('options') or [], ensure_ascii=False),
                'answer': json.dumps(portable.get('answer') if portable.get('answer') is not None else [], ensure_ascii=False),
                'analysis': portable.get('analysis') or '',
                'difficulty': int(portable.get('difficulty') or 1),
                'tags': json.dumps(portable.get('tags') or [], ensure_ascii=False),
                'image_path': data.get('image_path'),
                'created_by': uid,
            },
        )
        new_id = result.fetchone()[0]
        db.session.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
        
        return jsonify({'status':'success','message':'题目新增成功', 'id': new_id})
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500



@admin_api_bp.route('/questions/<int:question_id>', methods=['PUT'])
@subject_admin_required
def edit_question(question_id):
    """编辑题目"""
    data = request.json
    
    try:
        from app.core.utils.portable_question_format import internal_question_to_portable

        q_type = data.get('q_type')
        answer = (data.get('answer') or '').strip()
        options_str = data.get('options', '[]')
        
        # 多选题验证：确保答案至少有两个选项
        if q_type == '多选题':
            if len(answer) < 2:
                return jsonify({'status':'error','message':'多选题答案至少需要两个选项，例如：AB 或 ABC'}), 400
            # 验证答案中的所有字母是否在选项范围内
            try:
                options_list = json.loads(options_str) if isinstance(options_str, str) else options_str
                if isinstance(options_list, list) and len(options_list) > 0:
                    from app.core.utils.options_parser import parse_options
                    parsed_options = parse_options(options_list)
                    valid_keys = {opt['key'] for opt in parsed_options if opt.get('key')}
                    answer_keys = set(answer.upper())
                    invalid_keys = answer_keys - valid_keys
                    if invalid_keys:
                        return jsonify({'status':'error','message':f'多选题答案中包含无效选项：{", ".join(sorted(invalid_keys))}。有效选项为：{", ".join(sorted(valid_keys))}'}), 400
            except Exception:
                pass  # 如果解析选项失败，跳过验证
        
        portable = internal_question_to_portable(
            q_id=int(question_id),
            q_type=q_type,
            content=data.get('content'),
            options=options_str,
            answer=answer,
            explanation=data.get('explanation', ''),
            difficulty=data.get('difficulty', 1),
            tags=data.get('tags'),
        )

        db.session.execute(
            text('''
            UPDATE questions SET
                subject_id=:subject_id,
                type=:type,
                content=:content,
                options=:options,
                answer=:answer,
                analysis=:analysis,
                difficulty=:difficulty,
                tags=:tags,
                image_path=:image_path,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=:qid
            '''),
            {
                'subject_id': data.get('subject_id'),
                'type': portable.get('type') or 'essay',
                'content': portable.get('content') or '',
                'options': json.dumps(portable.get('options') or [], ensure_ascii=False),
                'answer': json.dumps(portable.get('answer') if portable.get('answer') is not None else [], ensure_ascii=False),
                'analysis': portable.get('analysis') or '',
                'difficulty': int(portable.get('difficulty') or 1),
                'tags': json.dumps(portable.get('tags') or [], ensure_ascii=False),
                'image_path': data.get('image_path'),
                'qid': int(question_id),
            },
        )
        db.session.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
        
        return jsonify({'status':'success','message':'题目修改成功'})
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500



@admin_api_bp.route('/questions/<int:question_id>', methods=['DELETE'])
@subject_admin_required
def delete_question(question_id):
    """删除题目"""
    db.session.execute(text('DELETE FROM questions WHERE id = :qid'), {'qid': question_id})
    db.session.commit()
    try:
        bump_questions_version()
    except Exception:
        pass
    
    return jsonify({'status': 'success', 'message': '题目删除成功'})



@admin_api_bp.route('/questions/batch_delete', methods=['POST'])
@subject_admin_required
def batch_delete_questions():
    """批量删除题目"""
    data = request.json
    ids = data.get('ids', [])
    
    if not ids:
        return jsonify({'status': 'error', 'message': '未提供要删除的题目 ID'}), 400
    
    try:
        for qid in ids:
            db.session.execute(text('DELETE FROM questions WHERE id = :qid'), {'qid': qid})
        db.session.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
        return jsonify({'status': 'success', 'message': '批量删除成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'批量删除失败: {str(e)}'}), 500



@admin_api_bp.route('/questions/batch_change_type', methods=['POST'])
@subject_admin_required
def batch_change_type():
    """批量修改题型"""
    data = request.json
    ids = data.get('ids', [])
    target_type = data.get('target_type')

    if not ids or not target_type:
        return jsonify({'status': 'error', 'message': '参数不完整'}), 400

    try:
        from app.core.utils.portable_question_format import (
            PORTABLE_TYPES,
            any_type_to_portable_type,
            internal_question_to_portable,
            portable_question_to_internal,
            portable_type_to_q_type,
        )

        target_portable = any_type_to_portable_type(target_type)
        if target_portable not in PORTABLE_TYPES:
            return jsonify({'status': 'error', 'message': '无效的目标题型'}), 400

        # 逐题重算 PQF（确保答案/填空占位符等与新题型语义一致）
        placeholders = ','.join([f':id_{i}' for i in range(len(ids))])
        id_params = {f'id_{i}': qid for i, qid in enumerate(ids)}
        rows = db.session.execute(
            text(f'''
            SELECT id, type, content, options, answer, analysis, tags, difficulty
            FROM questions
            WHERE id IN ({placeholders})
            '''),
            id_params,
        ).fetchall()

        updates = []
        for r in rows or []:
            rm = r._mapping
            try:
                qid = int(rm['id'])
            except Exception:
                continue

            try:
                p = {
                    'id': qid,
                    'type': rm['type'] or '',
                    'content': rm['content'] or '',
                    'options': json.loads(rm['options'] or '[]'),
                    'answer': json.loads(rm['answer'] or '[]'),
                    'analysis': rm['analysis'] or '',
                    'tags': json.loads(rm['tags'] or '[]'),
                    'difficulty': int(rm['difficulty'] or 1),
                }
            except Exception:
                p = {
                    'id': qid,
                    'type': rm['type'] or '',
                    'content': rm['content'] or '',
                    'options': [],
                    'answer': [],
                    'analysis': rm['analysis'] or '',
                    'tags': [],
                    'difficulty': 1,
                }

            internal, _errors = portable_question_to_internal(p, scope='question_center')
            target_q_type_cn = portable_type_to_q_type(target_portable)
            portable_new = internal_question_to_portable(
                q_id=qid,
                q_type=target_q_type_cn,
                content=internal.get('content') or '',
                options=internal.get('options') or [],
                answer=internal.get('answer') or '',
                explanation=internal.get('explanation') or '',
                difficulty=internal.get('difficulty') or 1,
                tags=internal.get('tags') or [],
            )

            updates.append(
                (
                    portable_new.get('type') or target_portable,
                    portable_new.get('content') or '',
                    json.dumps(portable_new.get('options') or [], ensure_ascii=False),
                    json.dumps(portable_new.get('answer') if portable_new.get('answer') is not None else [], ensure_ascii=False),
                    portable_new.get('analysis') or '',
                    json.dumps(portable_new.get('tags') or [], ensure_ascii=False),
                    int(portable_new.get('difficulty') or 1),
                    qid,
                )
            )

        if updates:
            for u in updates:
                db.session.execute(
                    text('''
                    UPDATE questions
                    SET type=:type,
                        content=:content,
                        options=:options,
                        answer=:answer,
                        analysis=:analysis,
                        tags=:tags,
                        difficulty=:difficulty,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=:qid
                    '''),
                    {
                        'type': u[0],
                        'content': u[1],
                        'options': u[2],
                        'answer': u[3],
                        'analysis': u[4],
                        'tags': u[5],
                        'difficulty': u[6],
                        'qid': u[7],
                    },
                )
        db.session.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
        return jsonify({'status': 'success', 'message': f'成功将 {len(ids)} 道题目修改为 "{target_type}"'}) 
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'批量修改题型失败: {str(e)}'}), 500



@admin_api_bp.route('/questions/batch_move_subject', methods=['POST'])
@subject_admin_required
def batch_move_subject():
    """批量移动题目到其他科目"""
    data = request.json
    ids = data.get('ids', [])
    target_subject_id = data.get('target_subject_id')
    
    if not ids or not target_subject_id:
        return jsonify({'status': 'error', 'message': '参数不完整'}), 400
    
    try:
        for qid in ids:
            db.session.execute(
                text('UPDATE questions SET subject_id = :sid WHERE id = :qid'),
                {'sid': target_subject_id, 'qid': qid},
            )
        db.session.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
        return jsonify({'status': 'success', 'message': f'成功移动 {len(ids)} 道题目'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'批量移动失败: {str(e)}'}), 500



@admin_api_bp.route('/questions/batch_set_difficulty', methods=['POST'])
@subject_admin_required
def batch_set_difficulty():
    """批量设置题目难度"""
    data = request.json
    ids = data.get('ids', [])
    difficulty = data.get('difficulty')
    
    if not ids or difficulty is None:
        return jsonify({'status': 'error', 'message': '参数不完整'}), 400
    
    try:
        for qid in ids:
            db.session.execute(
                text('UPDATE questions SET difficulty = :diff, updated_at=CURRENT_TIMESTAMP WHERE id = :qid'),
                {'diff': difficulty, 'qid': int(qid)},
            )
        db.session.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
        return jsonify({'status': 'success', 'message': f'成功设置 {len(ids)} 道题目的难度'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'批量设置难度失败: {str(e)}'}), 500



@admin_api_bp.route('/questions/batch_tags', methods=['POST'])
@subject_admin_required
def batch_tags():
    """批量操作标签"""
    data = request.json
    ids = data.get('ids', [])
    action = data.get('action')  # 'add', 'remove', 'set'
    tags = data.get('tags', '')
    
    if not ids or not action:
        return jsonify({'status': 'error', 'message': '参数不完整'}), 400
    
    try:
        new_tags_set = set(t.strip() for t in str(tags or '').split(',') if t and t.strip())

        for qid in ids:
            row = db.session.execute(text('SELECT id, tags FROM questions WHERE id = :qid'), {'qid': int(qid)}).fetchone()
            if not row:
                continue

            try:
                current_list = json.loads(row._mapping['tags'] or '[]')
                if not isinstance(current_list, list):
                    current_list = []
            except Exception:
                current_list = []
            current_set = set(str(t).strip() for t in current_list if str(t).strip())

            if action == 'add':
                current_set.update(new_tags_set)
            elif action == 'remove':
                current_set -= new_tags_set
            elif action == 'set':
                current_set = set(new_tags_set)

            cleaned = sorted(current_set)
            db.session.execute(
                text('UPDATE questions SET tags = :tags, updated_at=CURRENT_TIMESTAMP WHERE id = :qid'),
                {'tags': json.dumps(cleaned, ensure_ascii=False), 'qid': int(row._mapping['id'])},
            )

        db.session.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
        return jsonify({'status': 'success', 'message': f'成功处理 {len(ids)} 道题目的标签'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'批量操作标签失败: {str(e)}'}), 500



@admin_api_bp.route('/questions/duplicate-check/start', methods=['POST'])
@subject_admin_required
def start_duplicate_check():
    """启动查重并保存记录"""
    from app.modules.admin.services.duplicate_check_service import DuplicateCheckService
    
    subject_id = request.args.get('subject_id', type=int)
    similarity_threshold = request.args.get('similarity_threshold', 0.8, type=float)
    
    if not subject_id:
        return jsonify({'status': 'error', 'message': '科目ID不能为空'}), 400
    
    try:
        # 验证科目是否存在
        subject = db.session.execute(text('SELECT id FROM subjects WHERE id = :sid'), {'sid': subject_id}).fetchone()
        if not subject:
            return jsonify({'status': 'error', 'message': '科目不存在'}), 404
        
        # 获取当前用户ID
        user_id = session.get('user_id')
        
        # 执行查重并保存记录
        result = DuplicateCheckService.perform_and_save_duplicate_check(
            subject_id=subject_id,
            similarity_threshold=similarity_threshold,
            created_by=user_id
        )
        
        return jsonify({
            'status': 'success',
            'message': '查重完成并已保存',
            'data': result
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'启动查重失败: {str(e)}'}), 500



@admin_api_bp.route('/questions/duplicate-check/results', methods=['GET'])
@subject_admin_required
def get_duplicate_check_results():
    """获取查重结果（优先返回历史记录，如果没有则执行新查重）"""
    from app.modules.admin.services.duplicate_check_service import DuplicateCheckService
    
    subject_id = request.args.get('subject_id', type=int)
    min_similarity = request.args.get('min_similarity', type=float)
    max_similarity = request.args.get('max_similarity', type=float)
    force_new = request.args.get('force_new', 'false').lower() == 'true'  # 强制重新查重
    
    if not subject_id:
        return jsonify({'status': 'error', 'message': '科目ID不能为空'}), 400
    
    try:
        # 如果强制重新查重，或者没有历史记录，则执行新查重
        if force_new:
            # 执行新查重
            user_id = session.get('user_id')
            results = DuplicateCheckService.perform_and_save_duplicate_check(
                subject_id=subject_id,
                created_by=user_id
            )
            results['is_new'] = True
        else:
            # 尝试获取历史记录
            latest_record = DuplicateCheckService.get_latest_duplicate_check_record(subject_id)
            
            if latest_record:
                # 使用历史记录
                duplicates = latest_record.get('duplicates', [])
                
                # 获取科目信息
                subject = db.session.execute(
                    text('SELECT id, name FROM subjects WHERE id = :sid'),
                    {'sid': subject_id}
                ).fetchone()
                subject_name = dict(subject._mapping).get('name', '') if subject else ''
                
                # 应用相似度筛选
                if min_similarity is not None or max_similarity is not None:
                    filtered_duplicates = []
                    for dup in duplicates:
                        sim = dup.get('similarity', 0)
                        if min_similarity is not None and sim < min_similarity:
                            continue
                        if max_similarity is not None and sim > max_similarity:
                            continue
                        filtered_duplicates.append(dup)
                    duplicates = filtered_duplicates
                
                results = {
                    'record_id': latest_record.get('id'),
                    'total_pairs': latest_record.get('total_pairs', 0),
                    'duplicates': duplicates,
                    'subject_id': subject_id,
                    'subject_name': subject_name,
                    'created_at': latest_record.get('created_at'),
                    'is_new': False
                }
            else:
                # 没有历史记录，执行新查重
                user_id = session.get('user_id')
                results = DuplicateCheckService.perform_and_save_duplicate_check(
                    subject_id=subject_id,
                    created_by=user_id
                )
                results['is_new'] = True
        
        return jsonify({
            'status': 'success',
            'data': results
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'获取查重结果失败: {str(e)}'}), 500


