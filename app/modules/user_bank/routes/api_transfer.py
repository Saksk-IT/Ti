# -*- coding: utf-8 -*-

"""用户题库：导入/导出 API"""

import json

from flask import request, jsonify, current_app
from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.portable_question_format import (
    internal_question_to_portable,
    portable_question_to_internal,
)

from .api_base import user_bank_api_bp, check_bank_access


def _build_named_in(col: str, values: list, prefix: str = 'in') -> tuple[str, dict]:
    if not values:
        return f"{col} IN (NULL)", {}
    params = {f"{prefix}_{i}": v for i, v in enumerate(values)}
    placeholders = ', '.join(f':{k}' for k in params)
    return f"{col} IN ({placeholders})", params


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

    bank = db.session.execute(
        text('SELECT id, question_count FROM user_question_banks WHERE id = :bank_id AND user_id = :uid AND status = 1'),
        {'bank_id': bank_id, 'uid': user_id}
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    # 构建查询
    params: dict = {'uid': user_id}
    if source == 'mistakes':
        query = '''
            SELECT q.id, q.type, q.content, q.options, q.answer, q.analysis, q.difficulty, q.image_path
            FROM questions q
            JOIN mistakes m ON q.id = m.question_id
            WHERE m.user_id = :uid
        '''
        source_type = 'mistake'
    else:
        query = '''
            SELECT q.id, q.type, q.content, q.options, q.answer, q.analysis, q.difficulty, q.image_path
            FROM questions q
            JOIN favorites f ON q.id = f.question_id
            WHERE f.user_id = :uid
        '''
        source_type = 'favorite'

    if subject_id:
        query += ' AND q.subject_id = :subject_id'
        params['subject_id'] = subject_id

    if question_ids:
        in_clause, in_params = _build_named_in('q.id', question_ids, 'qid')
        query += f' AND {in_clause}'
        params.update(in_params)

    questions = db.session.execute(text(query), params).fetchall()

    if not questions:
        return jsonify({'code': 1, 'message': '未找到可导入的题目'}), 404

    imported_count = 0
    for q in questions:
        m = q._mapping
        db.session.execute(
            text('''
            INSERT INTO user_bank_questions
            (bank_id, user_id, type, content, options, answer, analysis, tags, difficulty, image_path,
             source_type, source_question_id, sort_order)
            VALUES (:bank_id, :uid, :qtype, :content, :options, :answer, :analysis, '[]', :difficulty, :image_path,
                    :source_type, :source_qid,
                    (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = :bank_id2))
            '''),
            {
                'bank_id': bank_id, 'uid': user_id,
                'qtype': m['type'] or 'essay', 'content': m['content'] or '',
                'options': m['options'] or '[]', 'answer': m['answer'] or '[]',
                'analysis': m['analysis'] or '', 'difficulty': int(m['difficulty'] or 1),
                'image_path': m['image_path'], 'source_type': source_type,
                'source_qid': m['id'], 'bank_id2': bank_id,
            },
        )
        imported_count += 1

    db.session.execute(
        text('UPDATE user_question_banks SET question_count = question_count + :cnt, updated_at = CURRENT_TIMESTAMP WHERE id = :bank_id'),
        {'cnt': imported_count, 'bank_id': bank_id}
    )
    db.session.commit()

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

    bank = db.session.execute(
        text('SELECT id, question_count FROM user_question_banks WHERE id = :bank_id AND user_id = :uid AND status = 1'),
        {'bank_id': bank_id, 'uid': user_id}
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
            # 兼容旧格式
            q_type = (q.get('题型') or q.get('q_type') or '').strip()
            content = q.get('题干') or q.get('content') or ''
            answer = q.get('答案') or q.get('answer') or ''
            explanation = q.get('解析') or q.get('explanation') or ''
            difficulty = q.get('难度') or q.get('difficulty') or 1
            tags = q.get('标签') or q.get('tags') or []

            content = str(content or '').replace('\r\n', '\n').replace('\r', '\n')
            answer = str(answer or '').replace('\r\n', '\n').replace('\r', '\n')
            explanation = str(explanation or '').replace('\r\n', '\n').replace('\r', '\n')

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
                q_id=None, q_type=q_type, content=content,
                options=options or [], answer=answer,
                explanation=explanation, difficulty=difficulty, tags=tags,
            )

            cursor = db.session.execute(
                text('''
                INSERT INTO user_bank_questions
                (bank_id, user_id, type, content, options, answer, analysis, tags, difficulty, source_type, sort_order)
                VALUES (:bank_id, :uid, :qtype, :content, :options, :answer, :analysis, :tags, :difficulty, 'custom',
                        (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = :bank_id2))
                RETURNING id
                '''),
                {
                    'bank_id': bank_id, 'uid': user_id,
                    'qtype': portable.get('type') or 'essay',
                    'content': portable.get('content') or '',
                    'options': json.dumps(portable.get('options') or [], ensure_ascii=False),
                    'answer': json.dumps(portable.get('answer') if portable.get('answer') is not None else [], ensure_ascii=False),
                    'analysis': portable.get('analysis') or '',
                    'tags': json.dumps(portable.get('tags') or [], ensure_ascii=False),
                    'difficulty': int(portable.get('difficulty') or 1),
                    'bank_id2': bank_id,
                },
            )
            imported_count += 1
            try:
                new_qid = int(cursor.fetchone()._mapping['id'])
            except Exception:
                new_qid = None
            if new_qid and tags:
                tag_pairs.append((new_qid, tags))
        except Exception as e:
            errors.append(f'第{idx+1}题: 导入失败 - {str(e)}')

    # 更新题目数量
    if imported_count > 0:
        db.session.execute(
            text('UPDATE user_question_banks SET question_count = question_count + :cnt, updated_at = CURRENT_TIMESTAMP WHERE id = :bank_id'),
            {'cnt': imported_count, 'bank_id': bank_id}
        )
        db.session.commit()

        # 同步标签
        if tag_pairs:
            try:
                from .api_tags import _load_bank_tag_store, _save_bank_tag_store

                raw_conn = db.session.connection()
                store = _load_bank_tag_store(raw_conn, bank_id, user_id)
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
                _save_bank_tag_store(raw_conn, bank_id, user_id, store)
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

    bank = db.session.execute(
        text('SELECT id FROM user_question_banks WHERE id = :bank_id AND user_id = :uid AND status = 1'),
        {'bank_id': bank_id, 'uid': user_id},
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
        extracted_text = extract_docx_text(raw)
        return jsonify({
            'code': 0,
            'data': {
                'filename': filename,
                'text': extracted_text,
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

    bank = db.session.execute(
        text('SELECT name FROM user_question_banks WHERE id = :bank_id'),
        {'bank_id': bank_id},
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在'}), 404

    selected_ids = _parse_question_ids_from_request_args()

    if selected_ids:
        in_clause, in_params = _build_named_in('id', selected_ids, 'sid')
        questions = db.session.execute(
            text(f'''
            SELECT id, type, content, options, answer, analysis, difficulty, image_path, source_type, created_at, updated_at
            FROM user_bank_questions
            WHERE bank_id = :bank_id AND {in_clause}
            ORDER BY sort_order ASC, id ASC
            '''),
            {'bank_id': bank_id, **in_params},
        ).fetchall()
    else:
        questions = db.session.execute(
            text('''
            SELECT id, type, content, options, answer, analysis, difficulty, image_path, source_type, created_at, updated_at
            FROM user_bank_questions
            WHERE bank_id = :bank_id
            ORDER BY sort_order ASC, id ASC
            '''),
            {'bank_id': bank_id},
        ).fetchall()

    if not questions:
        return jsonify({'code': 1, 'message': '题库中没有可导出的题目'}), 400

    # 题库标签（按当前用户维度）
    question_tags = {}
    try:
        from .api_tags import _load_bank_tag_store

        raw_conn = db.session.connection()
        store = _load_bank_tag_store(raw_conn, bank_id, user_id)
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
        m = q._mapping
        qid = int(m['id'])
        tags = question_tags.get(str(qid), [])
        items.append({
            'id': qid,
            'type': m['type'] or '',
            'content': m['content'] or '',
            'options': _safe_load(m['options'], []),
            'answer': _safe_load(m['answer'], []),
            'analysis': m['analysis'] or '',
            'tags': tags if isinstance(tags, list) else [],
            'difficulty': int(m['difficulty'] or 1),
        })

    export_payload = {'questions': items}
    export_payload_with_meta = {
        'meta': {
            'scope': 'user_bank',
            'bank_id': int(bank_id),
            'bank_name': bank._mapping['name'],
        },
        'questions': items,
    }

    download_flag = str(request.args.get('download') or '0').strip().lower()
    if download_flag in ('0', 'false', 'no', ''):
        return jsonify({'code': 0, 'data': export_payload_with_meta})

    buf = io.BytesIO(json.dumps(export_payload, ensure_ascii=False, indent=2).encode('utf-8'))
    filename = f"{bank._mapping['name']}_题库导出.json"
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

    bank = db.session.execute(
        text('SELECT name FROM user_question_banks WHERE id = :bank_id'),
        {'bank_id': bank_id}
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在'}), 404

    selected_ids = _parse_question_ids_from_request_args()

    if selected_ids:
        in_clause, in_params = _build_named_in('id', selected_ids, 'sid')
        questions = db.session.execute(
            text(f'''
            SELECT type, content, options, answer, analysis, difficulty
            FROM user_bank_questions
            WHERE bank_id = :bank_id AND {in_clause}
            ORDER BY sort_order ASC, id ASC
            '''),
            {'bank_id': bank_id, **in_params},
        ).fetchall()
    else:
        questions = db.session.execute(text('''
            SELECT type, content, options, answer, analysis, difficulty
            FROM user_bank_questions
            WHERE bank_id = :bank_id
            ORDER BY sort_order ASC, id ASC
        '''), {'bank_id': bank_id}).fetchall()

    if not questions:
        return jsonify({'code': 1, 'message': '题库中没有题目'}), 400

    from app.core.utils.pqf_rows import pqf_row_to_internal
    seed = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    export_data = []
    max_options = 0
    max_blanks = 0

    bank_name = bank._mapping['name']
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
            'subject': bank_name or '',
            'q_type': q_type_val,
            'content': content,
            'answer': answer_text if q_type_val != '填空题' else '',
            'explanation': explanation,
        }

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

    filename = f"{bank_name}_题目导出.xlsx"
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

    bank = db.session.execute(
        text('SELECT id, question_count FROM user_question_banks WHERE id = :bank_id AND user_id = :uid AND status = 1'),
        {'bank_id': bank_id, 'uid': user_id}
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': '没有文件'}), 400

    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.xlsx'):
        return jsonify({'code': 1, 'message': '请上传.xlsx格式的文件'}), 400

    try:
        try:
            df = pd.read_excel(file, sheet_name='题目示例').fillna('')
        except Exception:
            df = pd.read_excel(file).fillna('')

        required_cols = ['q_type', 'content']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            return jsonify({'code': 1, 'message': f'Excel文件缺少必需列: {", ".join(missing)}'}), 400

        import re

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
                errors.append(f'第{idx+2}行: answer 不能为空')
                continue

            options_str = json.dumps(options, ensure_ascii=False) if options else None

            portable = internal_question_to_portable(
                q_id=None, q_type=q_type, content=content,
                options=options_str or '[]', answer=answer,
                explanation=explanation, difficulty=difficulty, tags=[],
            )

            db.session.execute(
                text('''
                INSERT INTO user_bank_questions
                (bank_id, user_id, type, content, options, answer, analysis, tags, difficulty, source_type, sort_order)
                VALUES (:bank_id, :uid, :qtype, :content, :options, :answer, :analysis, '[]', :difficulty, 'custom',
                        (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = :bank_id2))
                '''),
                {
                    'bank_id': bank_id, 'uid': user_id,
                    'qtype': portable.get('type') or 'essay',
                    'content': portable.get('content') or '',
                    'options': json.dumps(portable.get('options') or [], ensure_ascii=False),
                    'answer': json.dumps(portable.get('answer') if portable.get('answer') is not None else [], ensure_ascii=False),
                    'analysis': portable.get('analysis') or '',
                    'difficulty': int(portable.get('difficulty') or 1),
                    'bank_id2': bank_id,
                },
            )
            imported_count += 1

        if imported_count > 0:
            db.session.execute(
                text('UPDATE user_question_banks SET question_count = question_count + :cnt, updated_at = CURRENT_TIMESTAMP WHERE id = :bank_id'),
                {'cnt': imported_count, 'bank_id': bank_id}
            )
            db.session.commit()

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

    bank = db.session.execute(
        text('SELECT name FROM user_question_banks WHERE id = :bank_id'),
        {'bank_id': bank_id}
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在'}), 404

    selected_ids = _parse_question_ids_from_request_args()
    if selected_ids:
        in_clause, in_params = _build_named_in('id', selected_ids, 'sid')
        questions = db.session.execute(
            text(f'''
            SELECT id, type, content, options, answer, analysis, difficulty, image_path
            FROM user_bank_questions
            WHERE bank_id = :bank_id AND {in_clause}
            ORDER BY sort_order ASC, id ASC
            '''),
            {'bank_id': bank_id, **in_params},
        ).fetchall()
    else:
        questions = db.session.execute(text('''
            SELECT id, type, content, options, answer, analysis, difficulty, image_path
            FROM user_bank_questions
            WHERE bank_id = :bank_id
            ORDER BY sort_order ASC, id ASC
        '''), {'bank_id': bank_id}).fetchall()

    if not questions:
        return jsonify({'code': 1, 'message': '题库中没有题目'}), 400

    question_tags = {}
    try:
        from .api_tags import _load_bank_tag_store

        raw_conn = db.session.connection()
        store = _load_bank_tag_store(raw_conn, bank_id, user_id)
        question_tags = store.get('question_tags', {}) or {}
    except Exception:
        question_tags = {}

    zip_buffer = io.BytesIO()
    upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, '..', 'uploads'))
    bank_name = bank._mapping['name']

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

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        questions_data = []
        image_count = 0

        for q in questions:
            m = q._mapping
            qid = int(m['id'])
            tags = question_tags.get(str(qid), [])
            q_data = {
                'id': qid,
                'type': m['type'] or '',
                'content': m['content'] or '',
                'options': _safe_load(m['options'], []),
                'answer': _safe_load(m['answer'], []),
                'analysis': m['analysis'] or '',
                'tags': tags if isinstance(tags, list) else [],
                'difficulty': int(m['difficulty'] or 1),
            }

            if m['image_path']:
                image_filename = os.path.basename(m['image_path'])
                full_path = os.path.join(upload_folder, m['image_path'].lstrip('/uploads/'))

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

        payload = {
            'meta': {
                'scope': 'user_bank_package',
                'bank_id': int(bank_id),
                'bank_name': bank_name,
            },
            'questions': questions_data,
        }
        zf.writestr('data.json', json.dumps(payload, ensure_ascii=False, indent=2))

    zip_buffer.seek(0)

    filename = f"{bank_name}_题库包.zip"
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

    bank = db.session.execute(
        text('SELECT id, question_count FROM user_question_banks WHERE id = :bank_id AND user_id = :uid AND status = 1'),
        {'bank_id': bank_id, 'uid': user_id}
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
            tag_pairs = []

            for idx, q in enumerate(questions_data):
                if not isinstance(q, dict):
                    errors.append(f'第{idx+1}题: 题目格式应为对象')
                    continue

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
                    q_id=None, q_type=q_type, content=content,
                    options=options or [], answer=answer,
                    explanation=explanation, difficulty=difficulty, tags=tags or [],
                )

                options_str = json.dumps(portable.get('options') or [], ensure_ascii=False)
                answer_str = json.dumps(
                    portable.get('answer') if portable.get('answer') is not None else [],
                    ensure_ascii=False,
                )
                tags_str = json.dumps(portable.get('tags') or [], ensure_ascii=False)

                image_path = None
                if images and isinstance(images, list) and images[0]:
                    src_image = str(images[0])
                    if src_image in zf.namelist():
                        img_data = zf.read(src_image)
                        ext = os.path.splitext(src_image)[1]
                        new_filename = f"user_bank_{bank_id}_{uuid.uuid4().hex}{ext}"
                        new_path = os.path.join(upload_folder, 'questions', new_filename)
                        os.makedirs(os.path.dirname(new_path), exist_ok=True)

                        with open(new_path, 'wb') as img_file:
                            img_file.write(img_data)

                        image_path = f"/uploads/questions/{new_filename}"

                cursor = db.session.execute(text('''
                    INSERT INTO user_bank_questions
                    (bank_id, user_id, type, content, options, answer, analysis, tags, difficulty, image_path, source_type, sort_order)
                    VALUES (:bank_id, :uid, :qtype, :content, :options, :answer, :analysis, :tags, :difficulty, :image_path, 'custom',
                            (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = :bank_id2))
                    RETURNING id
                '''), {
                    'bank_id': bank_id, 'uid': user_id,
                    'qtype': portable.get('type') or 'essay',
                    'content': portable.get('content') or '',
                    'options': options_str, 'answer': answer_str,
                    'analysis': portable.get('analysis') or '',
                    'tags': tags_str,
                    'difficulty': int(portable.get('difficulty') or 1),
                    'image_path': image_path,
                    'bank_id2': bank_id,
                })
                imported_count += 1
                try:
                    new_qid = int(cursor.fetchone()._mapping['id'])
                except Exception:
                    new_qid = None
                if new_qid and (portable.get('tags') or []):
                    tag_pairs.append((new_qid, portable.get('tags') or []))

            if imported_count > 0:
                db.session.execute(
                    text('UPDATE user_question_banks SET question_count = question_count + :cnt, updated_at = CURRENT_TIMESTAMP WHERE id = :bank_id'),
                    {'cnt': imported_count, 'bank_id': bank_id}
                )
                db.session.commit()

                if tag_pairs:
                    try:
                        from .api_tags import _load_bank_tag_store, _save_bank_tag_store

                        raw_conn = db.session.connection()
                        store = _load_bank_tag_store(raw_conn, bank_id, user_id)
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
                        _save_bank_tag_store(raw_conn, bank_id, user_id, store)
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
