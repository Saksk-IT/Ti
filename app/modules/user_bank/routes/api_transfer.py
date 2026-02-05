# -*- coding: utf-8 -*-

"""用户题库：导入/导出 API"""

import json

from flask import request, jsonify, current_app

from app.core.utils.database import get_db
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.portable_question_format import (
    internal_question_to_portable,
    portable_question_to_internal,
)

from .api_base import user_bank_api_bp, check_bank_access


@user_bank_api_bp.route('/<int:bank_id>/questions/import', methods=['POST'])
@auth_required
def import_questions(bank_id):
    """从错题本/收藏夹导入题目"""
    user_id = current_user_id()
    data = request.get_json() or {}
    source = data.get('source')  # 'mistakes' or 'favorites'
    subject_id = data.get('subject_id')
    question_ids = data.get('question_ids', [])

    if source not in ('mistakes', 'favorites'):
        return jsonify({'code': 1, 'message': '无效的来源'}), 400

    conn = get_db()

    bank = conn.execute(
        'SELECT id, question_count FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    # 构建查询
    if source == 'mistakes':
        query = '''
            SELECT q.id, q.type, q.content, q.options, q.answer, q.analysis, q.difficulty, q.image_path
            FROM questions q
            JOIN mistakes m ON q.id = m.question_id
            WHERE m.user_id = ?
        '''
        source_type = 'mistake'
    else:
        query = '''
            SELECT q.id, q.type, q.content, q.options, q.answer, q.analysis, q.difficulty, q.image_path
            FROM questions q
            JOIN favorites f ON q.id = f.question_id
            WHERE f.user_id = ?
        '''
        source_type = 'favorite'

    params = [user_id]

    if subject_id:
        query += ' AND q.subject_id = ?'
        params.append(subject_id)

    if question_ids:
        placeholders = ','.join(['?'] * len(question_ids))
        query += f' AND q.id IN ({placeholders})'
        params.extend(question_ids)

    questions = conn.execute(query, params).fetchall()

    if not questions:
        return jsonify({'code': 1, 'message': '未找到可导入的题目'}), 404

    imported_count = 0
    for q in questions:
        conn.execute(
            '''
            INSERT INTO user_bank_questions
            (bank_id, user_id, type, content, options, answer, analysis, tags, difficulty, image_path,
             source_type, source_question_id, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, '[]', ?, ?, ?, ?,
                    (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = ?))
            ''',
            (
                bank_id,
                user_id,
                q['type'] or 'essay',
                q['content'] or '',
                q['options'] or '[]',
                q['answer'] or '[]',
                q['analysis'] or '',
                int(q['difficulty'] or 1),
                q['image_path'],
                source_type,
                q['id'],
                bank_id,
            ),
        )
        imported_count += 1

    conn.execute(
        'UPDATE user_question_banks SET question_count = question_count + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (imported_count, bank_id)
    )
    conn.commit()

    return jsonify({'code': 0, 'message': f'成功导入{imported_count}道题目'})


@user_bank_api_bp.route('/<int:bank_id>/questions/import/json', methods=['POST'])
@auth_required
def import_questions_json(bank_id):
    """直接导入题目数据（JSON格式）"""
    user_id = current_user_id()
    data = request.get_json() or {}
    questions = data.get('questions', [])

    if not questions or not isinstance(questions, list):
        return jsonify({'code': 1, 'message': '请提供有效的题目数据'}), 400

    conn = get_db()

    bank = conn.execute(
        'SELECT id, question_count FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    imported_count = 0
    errors = []
    tag_pairs = []  # [(new_question_id, tags_list)]

    for idx, q in enumerate(questions):
        if not isinstance(q, dict):
            errors.append(f'第{idx+1}题: 题目格式应为对象')
            continue

        # 新统一格式：{type, content, options, answer, analysis, tags, difficulty}
        if 'type' in q or (isinstance(q.get('answer'), list) and 'content' in q):
            internal, conv_errors = portable_question_to_internal(q, scope='user_bank')
            if conv_errors:
                errors.append(f'第{idx+1}题: ' + '；'.join(conv_errors))
                continue

            q_type = (internal.get('q_type') or '').strip()
            content = internal.get('content') or ''
            options = internal.get('options') or []
            answer = internal.get('answer') or ''
            explanation = internal.get('explanation') or ''
            difficulty = internal.get('difficulty') or 1
            tags = internal.get('tags') or []
        else:
            # 兼容旧格式（题型/题干/选项/答案/解析/难度）
            q_type = (q.get('题型') or q.get('q_type') or '').strip()
            content = q.get('题干') or q.get('content') or ''
            answer = q.get('答案') or q.get('answer') or ''
            explanation = q.get('解析') or q.get('explanation') or ''
            difficulty = q.get('难度') or q.get('difficulty') or 1
            tags = q.get('标签') or q.get('tags') or []

            # 保留题干/答案/解析的缩进与换行；仅用于校验时做 strip 判断。
            content = str(content or '').replace('\r\n', '\n').replace('\r', '\n')
            answer = str(answer or '').replace('\r\n', '\n').replace('\r', '\n')
            explanation = str(explanation or '').replace('\r\n', '\n').replace('\r', '\n')

            # 处理选项
            options = q.get('选项') or q.get('options') or []
            if isinstance(options, str):
                try:
                    options = json.loads(options)
                except Exception:
                    options = []
            if isinstance(options, list):
                options = [str(o) for o in options]

        try:
            difficulty = int(difficulty or 1)
        except Exception:
            difficulty = 1
        difficulty = max(1, min(5, difficulty))

        if not q_type or not str(content or '').strip():
            errors.append(f'第{idx+1}题: 题型或题干为空')
            continue

        try:
            portable = internal_question_to_portable(
                q_id=None,
                q_type=q_type,
                content=content,
                options=options or [],
                answer=answer,
                explanation=explanation,
                difficulty=difficulty,
                tags=tags,
            )

            cursor = conn.execute(
                '''
                INSERT INTO user_bank_questions
                (bank_id, user_id, type, content, options, answer, analysis, tags, difficulty, source_type, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'custom',
                        (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = ?))
                ''',
                (
                    bank_id,
                    user_id,
                    portable.get('type') or 'essay',
                    portable.get('content') or '',
                    json.dumps(portable.get('options') or [], ensure_ascii=False),
                    json.dumps(portable.get('answer') if portable.get('answer') is not None else [], ensure_ascii=False),
                    portable.get('analysis') or '',
                    json.dumps(portable.get('tags') or [], ensure_ascii=False),
                    int(portable.get('difficulty') or 1),
                    bank_id,
                ),
            )
            imported_count += 1
            try:
                new_qid = int(cursor.lastrowid)
            except Exception:
                new_qid = None
            if new_qid and tags:
                tag_pairs.append((new_qid, tags))
        except Exception as e:
            errors.append(f'第{idx+1}题: 导入失败 - {str(e)}')

    # 更新题目数量
    if imported_count > 0:
        conn.execute(
            'UPDATE user_question_banks SET question_count = question_count + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (imported_count, bank_id)
        )
        conn.commit()

        # 同步标签（存储于 user_progress 的 bank_x_tags）
        if tag_pairs:
            try:
                from .api_tags import _load_bank_tag_store, _save_bank_tag_store

                store = _load_bank_tag_store(conn, bank_id, user_id)
                all_tags = store.get('tags', []) or []
                q_tags = store.get('question_tags', {}) or {}

                for q_id, tags in tag_pairs:
                    cleaned = [str(t).strip() for t in (tags or []) if str(t).strip()]
                    if not cleaned:
                        continue
                    for t in cleaned:
                        if t not in all_tags:
                            all_tags.append(t)
                    q_tags[str(q_id)] = cleaned

                store['tags'] = all_tags
                store['question_tags'] = q_tags
                _save_bank_tag_store(conn, bank_id, user_id, store)
            except Exception:
                pass

    return jsonify({
        'code': 0,
        'data': {
            'imported': imported_count,
            'errors': errors[:10]
        },
        'message': f'成功导入{imported_count}道题目' + (f'，{len(errors)}条错误' if errors else '')
    })


@user_bank_api_bp.route('/<int:bank_id>/questions/import/word/extract', methods=['POST'])
@auth_required
def extract_questions_word_docx(bank_id: int):
    """从 Word(.docx) 提取原始文本（供前端解析/预览使用）。"""
    user_id = current_user_id()
    conn = get_db()

    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id),
    ).fetchone()
    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': '没有文件'}), 400

    file = request.files['file']
    filename = file.filename or ''
    if not filename or not filename.lower().endswith('.docx'):
        return jsonify({'code': 1, 'message': '请上传.docx格式的文件'}), 400

    try:
        from app.core.utils.docx_text_extractor import extract_docx_text

        raw = file.read()
        text = extract_docx_text(raw)
        return jsonify({
            'code': 0,
            'data': {
                'filename': filename,
                'text': text,
            }
        })
    except Exception as e:
        try:
            current_app.logger.exception('extract_questions_word_docx failed: %s', str(e))
        except Exception:
            pass
        return jsonify({'code': 1, 'message': f'解析失败: {str(e)}'}), 500


def _parse_question_ids_from_request_args():
    raw = (request.args.get('ids') or request.args.get('question_ids') or '').strip()
    ids = []

    if raw:
        for part in raw.replace(' ', '').split(','):
            if not part:
                continue
            try:
                ids.append(int(part))
            except Exception:
                continue
    else:
        for key in ('id', 'question_id', 'question_ids'):
            for v in request.args.getlist(key):
                try:
                    ids.append(int(v))
                except Exception:
                    continue

    if not ids:
        return []

    # 去重但保留顺序
    seen = set()
    result = []
    for i in ids:
        if i in seen:
            continue
        seen.add(i)
        result.append(i)
    return result


@user_bank_api_bp.route('/<int:bank_id>/questions/export', methods=['GET'])
@auth_required
def export_questions_json(bank_id):
    """导出题目为JSON文件"""
    import io
    import json
    from flask import send_file

    user_id = current_user_id()
    has_access, _permission, _access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    conn = get_db()

    bank = conn.execute(
        'SELECT name FROM user_question_banks WHERE id = ?',
        (bank_id,),
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在'}), 404

    selected_ids = _parse_question_ids_from_request_args()

    if selected_ids:
        placeholders = ','.join(['?'] * len(selected_ids))
        questions = conn.execute(
            f'''
            SELECT id, type, content, options, answer, analysis, difficulty, image_path, source_type, created_at, updated_at
            FROM user_bank_questions
            WHERE bank_id = ? AND id IN ({placeholders})
            ORDER BY sort_order ASC, id ASC
            ''',
            [bank_id, *selected_ids],
        ).fetchall()
    else:
        questions = conn.execute(
            '''
            SELECT id, type, content, options, answer, analysis, difficulty, image_path, source_type, created_at, updated_at
            FROM user_bank_questions
            WHERE bank_id = ?
            ORDER BY sort_order ASC, id ASC
            ''',
            (bank_id,),
        ).fetchall()

    if not questions:
        return jsonify({'code': 1, 'message': '题库中没有可导出的题目'}), 400

    # 题库标签（按当前用户维度）
    question_tags = {}
    try:
        from .api_tags import _load_bank_tag_store

        store = _load_bank_tag_store(conn, bank_id, user_id)
        question_tags = store.get('question_tags', {}) or {}
    except Exception:
        question_tags = {}

    def _safe_load(raw, default):
        if raw is None:
            return default
        if isinstance(raw, (list, dict, bool, int, float)):
            return raw
        s = str(raw).strip()
        if not s:
            return default
        try:
            return json.loads(s)
        except Exception:
            return default

    items = []
    for q in questions:
        qid = int(q['id'])
        tags = question_tags.get(str(qid), [])
        items.append(
            {
                'id': qid,
                'type': q['type'] or '',
                'content': q['content'] or '',
                'options': _safe_load(q['options'], []),
                'answer': _safe_load(q['answer'], []),
                'analysis': q['analysis'] or '',
                'tags': tags if isinstance(tags, list) else [],
                'difficulty': int(q['difficulty'] or 1),
            }
        )

    # 文件导出遵循 PQF 标准：顶层仅包含 questions（其余信息可忽略或由调用方自行记录）
    export_payload = {
        'questions': items,
    }
    # API 返回可附带 meta（不影响导入端按 questions 解析）
    export_payload_with_meta = {
        'meta': {
            'scope': 'user_bank',
            'bank_id': int(bank_id),
            'bank_name': bank['name'],
        },
        'questions': items,
    }

    download_flag = str(request.args.get('download') or '0').strip().lower()
    if download_flag in ('0', 'false', 'no', ''):
        return jsonify({'code': 0, 'data': export_payload_with_meta})

    buf = io.BytesIO(json.dumps(export_payload, ensure_ascii=False, indent=2).encode('utf-8'))
    filename = f"{bank['name']}_题库导出.json"
    return send_file(
        buf,
        mimetype='application/json',
        as_attachment=True,
        download_name=filename,
    )


@user_bank_api_bp.route('/<int:bank_id>/questions/export/excel', methods=['GET'])
@auth_required
def export_questions_excel(bank_id):
    """导出题目为Excel文件（与导入模板一致）"""
    import pandas as pd
    import io
    from flask import send_file

    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    conn = get_db()

    # 获取题库信息
    bank = conn.execute(
        'SELECT name FROM user_question_banks WHERE id = ?',
        (bank_id,)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在'}), 404

    selected_ids = _parse_question_ids_from_request_args()

    # 获取题目
    if selected_ids:
        placeholders = ','.join(['?'] * len(selected_ids))
        questions = conn.execute(
            f'''
            SELECT type, content, options, answer, analysis, difficulty
            FROM user_bank_questions
            WHERE bank_id = ? AND id IN ({placeholders})
            ORDER BY sort_order ASC, id ASC
            ''',
            [bank_id, *selected_ids],
        ).fetchall()
    else:
        questions = conn.execute('''
            SELECT type, content, options, answer, analysis, difficulty
            FROM user_bank_questions
            WHERE bank_id = ?
            ORDER BY sort_order ASC, id ASC
        ''', (bank_id,)).fetchall()

    if not questions:
        return jsonify({'code': 1, 'message': '题库中没有题目'}), 400

    from app.core.utils.pqf_rows import pqf_row_to_internal
    seed = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    # 准备数据（列名遵循 instance/question_import_template.xlsx）
    export_data = []
    max_options = 0
    max_blanks = 0

    for q in questions:
        internal = pqf_row_to_internal(q, scope='user_bank')
        q_type_val = internal.get('q_type') or ''

        content = internal.get('content') or ''
        answer_text = internal.get('answer') or ''
        explanation = internal.get('explanation') or ''
        options = internal.get('options') or []

        blank_answers = []
        if q_type_val == '填空题' and answer_text:
            blank_answers = str(answer_text).split(';;')

        max_options = max(max_options, len(options))
        max_blanks = max(max_blanks, len(blank_answers))

        row = {
            'subject': bank['name'] or '',
            'q_type': q_type_val,
            'content': content,
            'answer': answer_text if q_type_val != '填空题' else '',
            'explanation': explanation,
        }

        # 选项列：移除可能的 "A. " 前缀，与模板一致
        for i, opt in enumerate(options):
            opt_text = str(opt or '')
            prefix = f"{seed[i]}. " if i < len(seed) else f"{i+1}. "
            if opt_text.startswith(prefix):
                opt_text = opt_text[len(prefix):]
            col = f"option_{seed[i]}" if i < len(seed) else f"option_{i+1}"
            row[col] = opt_text

        for i, blank in enumerate(blank_answers):
            row[f'blank_{i+1}'] = blank

        export_data.append(row)

    columns = ['subject', 'q_type', 'content']
    for i in range(max_options):
        columns.append(f"option_{seed[i]}" if i < len(seed) else f"option_{i+1}")
    columns.append('answer')
    for i in range(max_blanks):
        columns.append(f'blank_{i+1}')
    columns.append('explanation')

    df = pd.DataFrame(export_data)
    for col in columns:
        if col not in df.columns:
            df[col] = ''
    df = df[columns]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='题目示例', index=False)

    output.seek(0)

    filename = f"{bank['name']}_题目导出.xlsx"
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@user_bank_api_bp.route('/<int:bank_id>/questions/import/excel', methods=['POST'])
@auth_required
def import_questions_excel(bank_id):
    """从Excel文件导入题目（与导入模板一致）"""
    import pandas as pd
    import json

    user_id = current_user_id()
    conn = get_db()

    bank = conn.execute(
        'SELECT id, question_count FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': '没有文件'}), 400

    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.xlsx'):
        return jsonify({'code': 1, 'message': '请上传.xlsx格式的文件'}), 400

    try:
        # 优先读取模板同名 sheet（不存在则回退到默认第一张）
        try:
            df = pd.read_excel(file, sheet_name='题目示例').fillna('')
        except Exception:
            df = pd.read_excel(file).fillna('')

        # 检查必需列
        required_cols = ['q_type', 'content']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            return jsonify({'code': 1, 'message': f'Excel文件缺少必需列: {", ".join(missing)}'}), 400

        import re

        # 获取选项/填空列（同时兼容 option_A/option_1 与 blank_1...）
        option_cols_raw = [col for col in df.columns if str(col).startswith('option_')]
        blank_cols_raw = [col for col in df.columns if str(col).startswith('blank_')]

        seed = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        def _opt_key(col_name: str):
            s = str(col_name)
            m = re.match(r'^option_([A-Za-z])$', s)
            if m:
                letter = m.group(1).upper()
                return (0, seed.index(letter) if letter in seed else 999)
            m = re.match(r'^option_(\d+)$', s)
            if m:
                return (1, int(m.group(1)))
            return (2, s)

        def _blank_key(col_name: str):
            s = str(col_name)
            m = re.match(r'^blank_(\d+)$', s)
            return int(m.group(1)) if m else 999

        option_cols = sorted(option_cols_raw, key=_opt_key)
        blank_cols = sorted(blank_cols_raw, key=_blank_key)

        imported_count = 0
        errors = []

        for idx, row in df.iterrows():
            q_type = str(row.get('q_type', '')).strip()
            content = str(row.get('content', '')).strip()
            answer = str(row.get('answer', '')).strip()
            explanation = str(row.get('explanation', '')).strip()
            difficulty = int(row.get('difficulty', 1)) if row.get('difficulty') else 1

            if not q_type or not content:
                errors.append(f'第{idx+2}行: 题型或题干为空')
                continue

            # 处理选项
            options = []
            if q_type in ('选择题', '多选题'):
                for col in option_cols:
                    opt = str(row.get(col, '')).strip()
                    if opt:
                        options.append(opt)
                if len(options) < 2:
                    errors.append(f'第{idx+2}行: 选择题/多选题至少需要2个选项')
                    continue
                if not answer:
                    errors.append(f'第{idx+2}行: 选择题/多选题的 answer 不能为空')
                    continue

            # 填空题：优先使用 blank_* 列；无 blank_* 时回退到 answer（兼容旧格式）
            if q_type == '填空题':
                blanks = []
                for col in blank_cols:
                    blank_text = str(row.get(col, '')).strip()
                    if blank_text:
                        blanks.append(blank_text)
                if blanks:
                    answer = ';;'.join(blanks)
                if not answer:
                    errors.append(f'第{idx+2}行: 填空题至少需要一个 blank_* 或 answer')
                    continue

            if q_type not in ('填空题',) and not answer:
                # 判断题/简答题同样需要答案（与模板说明一致）
                errors.append(f'第{idx+2}行: answer 不能为空')
                continue

            options_str = json.dumps(options, ensure_ascii=False) if options else None

            portable = internal_question_to_portable(
                q_id=None,
                q_type=q_type,
                content=content,
                options=options_str or '[]',
                answer=answer,
                explanation=explanation,
                difficulty=difficulty,
                tags=[],
            )

            # 插入题目（PQF 同名列）
            conn.execute(
                '''
                INSERT INTO user_bank_questions
                (bank_id, user_id, type, content, options, answer, analysis, tags, difficulty, source_type, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, '[]', ?, 'custom',
                        (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = ?))
                ''',
                (
                    bank_id,
                    user_id,
                    portable.get('type') or 'essay',
                    portable.get('content') or '',
                    json.dumps(portable.get('options') or [], ensure_ascii=False),
                    json.dumps(portable.get('answer') if portable.get('answer') is not None else [], ensure_ascii=False),
                    portable.get('analysis') or '',
                    int(portable.get('difficulty') or 1),
                    bank_id,
                ),
            )
            imported_count += 1

        # 更新题目数量
        if imported_count > 0:
            conn.execute(
                'UPDATE user_question_banks SET question_count = question_count + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (imported_count, bank_id)
            )
            conn.commit()

        return jsonify({
            'code': 0,
            'data': {
                'imported': imported_count,
                'errors': errors[:10]  # 最多返回10条错误
            },
            'message': f'成功导入{imported_count}道题目' + (f'，{len(errors)}条错误' if errors else '')
        })

    except Exception as e:
        return jsonify({'code': 1, 'message': f'导入失败: {str(e)}'}), 500


@user_bank_api_bp.route('/<int:bank_id>/questions/export/package', methods=['GET'])
@auth_required
def export_questions_package(bank_id):
    """导出题目包（ZIP格式，含图片）"""
    import json
    import zipfile
    import io
    import os
    from flask import send_file

    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    conn = get_db()

    bank = conn.execute(
        'SELECT name FROM user_question_banks WHERE id = ?',
        (bank_id,)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在'}), 404

    selected_ids = _parse_question_ids_from_request_args()
    if selected_ids:
        placeholders = ','.join(['?'] * len(selected_ids))
        questions = conn.execute(
            f'''
            SELECT id, type, content, options, answer, analysis, difficulty, image_path
            FROM user_bank_questions
            WHERE bank_id = ? AND id IN ({placeholders})
            ORDER BY sort_order ASC, id ASC
            ''',
            [bank_id, *selected_ids],
        ).fetchall()
    else:
        questions = conn.execute('''
            SELECT id, type, content, options, answer, analysis, difficulty, image_path
            FROM user_bank_questions
            WHERE bank_id = ?
            ORDER BY sort_order ASC, id ASC
        ''', (bank_id,)).fetchall()

    if not questions:
        return jsonify({'code': 1, 'message': '题库中没有题目'}), 400

    # 标签（按当前用户维度）
    question_tags = {}
    try:
        from .api_tags import _load_bank_tag_store

        store = _load_bank_tag_store(conn, bank_id, user_id)
        question_tags = store.get('question_tags', {}) or {}
    except Exception:
        question_tags = {}

    # 创建ZIP
    zip_buffer = io.BytesIO()
    upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, '..', 'uploads'))

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        questions_data = []
        image_count = 0

        def _safe_load(raw, default):
            if raw is None:
                return default
            if isinstance(raw, (list, dict, bool, int, float)):
                return raw
            s = str(raw).strip()
            if not s:
                return default
            try:
                return json.loads(s)
            except Exception:
                return default

        for q in questions:
            qid = int(q['id'])
            tags = question_tags.get(str(qid), [])
            q_data = {
                'id': qid,
                'type': q['type'] or '',
                'content': q['content'] or '',
                'options': _safe_load(q['options'], []),
                'answer': _safe_load(q['answer'], []),
                'analysis': q['analysis'] or '',
                'tags': tags if isinstance(tags, list) else [],
                'difficulty': int(q['difficulty'] or 1),
            }

            # 处理图片
            if q['image_path']:
                image_filename = os.path.basename(q['image_path'])
                full_path = os.path.join(upload_folder, q['image_path'].lstrip('/uploads/'))

                if os.path.exists(full_path):
                    new_image_name = f"images/{image_count}_{image_filename}"
                    zf.write(full_path, new_image_name)
                    q_data['images'] = [new_image_name]
                    image_count += 1
                else:
                    q_data['images'] = []
            else:
                q_data['images'] = []

            questions_data.append(q_data)

        # 写入data.json
        payload = {
            'meta': {
                'scope': 'user_bank_package',
                'bank_id': int(bank_id),
                'bank_name': bank['name'],
            },
            'questions': questions_data,
        }
        zf.writestr('data.json', json.dumps(payload, ensure_ascii=False, indent=2))

    zip_buffer.seek(0)

    filename = f"{bank['name']}_题库包.zip"
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=filename
    )


@user_bank_api_bp.route('/<int:bank_id>/questions/import/package', methods=['POST'])
@auth_required
def import_questions_package(bank_id):
    """导入题目包（ZIP格式）"""
    import json
    import zipfile
    import os
    import uuid

    user_id = current_user_id()
    conn = get_db()

    bank = conn.execute(
        'SELECT id, question_count FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': '没有文件'}), 400

    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.zip'):
        return jsonify({'code': 1, 'message': '请上传.zip格式的文件'}), 400

    upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, '..', 'uploads'))

    try:
        with zipfile.ZipFile(file, 'r') as zf:
            if 'data.json' not in zf.namelist():
                return jsonify({'code': 1, 'message': '压缩包中缺少data.json文件'}), 400

            with zf.open('data.json') as f:
                raw_payload = json.load(f)
                if isinstance(raw_payload, dict) and isinstance(raw_payload.get('questions'), list):
                    questions_data = raw_payload.get('questions') or []
                elif isinstance(raw_payload, list):
                    questions_data = raw_payload
                else:
                    return jsonify({'code': 1, 'message': 'data.json 格式不支持'}), 400

            imported_count = 0
            errors = []
            tag_pairs = []  # [(new_question_id, tags_list)]

            for idx, q in enumerate(questions_data):
                if not isinstance(q, dict):
                    errors.append(f'第{idx+1}题: 题目格式应为对象')
                    continue

                # 新统一格式
                if 'type' in q or (isinstance(q.get('answer'), list) and 'content' in q):
                    internal, conv_errors = portable_question_to_internal(q, scope='user_bank')
                    if conv_errors:
                        errors.append(f'第{idx+1}题: ' + '；'.join(conv_errors))
                        continue

                    q_type = (internal.get('q_type') or '').strip()
                    content = (internal.get('content') or '').strip()
                    answer = internal.get('answer') or ''
                    explanation = internal.get('explanation') or ''
                    difficulty = internal.get('difficulty') or 1
                    options = internal.get('options') or []
                    tags = internal.get('tags') or []
                    images = q.get('images') or []
                else:
                    # 兼容旧包格式
                    q_type = str(q.get('q_type', '')).strip()
                    content = str(q.get('content', '')).strip()
                    answer = q.get('answer', '')
                    explanation = q.get('explanation', '')
                    difficulty = q.get('difficulty', 1)
                    options = q.get('options', [])
                    tags = q.get('tags') or q.get('标签') or []
                    images = q.get('images') or ([] if not q.get('image_path') else [q.get('image_path')])

                if not q_type or not content:
                    errors.append(f'第{idx+1}题: 题型或题干为空')
                    continue

                portable = internal_question_to_portable(
                    q_id=None,
                    q_type=q_type,
                    content=content,
                    options=options or [],
                    answer=answer,
                    explanation=explanation,
                    difficulty=difficulty,
                    tags=tags or [],
                )

                options_str = json.dumps(portable.get('options') or [], ensure_ascii=False)
                answer_str = json.dumps(
                    portable.get('answer') if portable.get('answer') is not None else [],
                    ensure_ascii=False,
                )
                tags_str = json.dumps(portable.get('tags') or [], ensure_ascii=False)

                # 处理图片
                image_path = None
                if images and isinstance(images, list) and images[0]:
                    src_image = str(images[0])
                    if src_image in zf.namelist():
                        # 保存图片
                        img_data = zf.read(src_image)
                        ext = os.path.splitext(src_image)[1]
                        new_filename = f"user_bank_{bank_id}_{uuid.uuid4().hex}{ext}"
                        new_path = os.path.join(upload_folder, 'questions', new_filename)
                        os.makedirs(os.path.dirname(new_path), exist_ok=True)

                        with open(new_path, 'wb') as img_file:
                            img_file.write(img_data)

                        image_path = f"/uploads/questions/{new_filename}"

                # 插入题目
                cursor = conn.execute('''
                    INSERT INTO user_bank_questions
                    (bank_id, user_id, type, content, options, answer, analysis, tags, difficulty, image_path, source_type, sort_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'custom',
                            (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = ?))
                ''', (
                    bank_id,
                    user_id,
                    portable.get('type') or 'essay',
                    portable.get('content') or '',
                    options_str,
                    answer_str,
                    portable.get('analysis') or '',
                    tags_str,
                    int(portable.get('difficulty') or 1),
                    image_path,
                    bank_id,
                ))
                imported_count += 1
                try:
                    new_qid = int(cursor.lastrowid)
                except Exception:
                    new_qid = None
                if new_qid and (portable.get('tags') or []):
                    tag_pairs.append((new_qid, portable.get('tags') or []))

            # 更新题目数量
            if imported_count > 0:
                conn.execute(
                    'UPDATE user_question_banks SET question_count = question_count + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                    (imported_count, bank_id)
                )
                conn.commit()

                if tag_pairs:
                    try:
                        from .api_tags import _load_bank_tag_store, _save_bank_tag_store

                        store = _load_bank_tag_store(conn, bank_id, user_id)
                        all_tags = store.get('tags', []) or []
                        q_tags = store.get('question_tags', {}) or {}

                        for q_id, tags in tag_pairs:
                            cleaned = [str(t).strip() for t in (tags or []) if str(t).strip()]
                            if not cleaned:
                                continue
                            for t in cleaned:
                                if t not in all_tags:
                                    all_tags.append(t)
                            q_tags[str(q_id)] = cleaned

                        store['tags'] = all_tags
                        store['question_tags'] = q_tags
                        _save_bank_tag_store(conn, bank_id, user_id, store)
                    except Exception:
                        pass

            return jsonify({
                'code': 0,
                'data': {
                    'imported': imported_count,
                    'errors': errors[:10]
                },
                'message': f'成功导入{imported_count}道题目' + (f'，{len(errors)}条错误' if errors else '')
            })

    except Exception as e:
        return jsonify({'code': 1, 'message': f'导入失败: {str(e)}'}), 500
