# -*- coding: utf-8 -*-

import json
import uuid
from datetime import datetime, timedelta

from flask import request, jsonify, current_app

from app.core.utils.database import get_db
from app.core.utils.decorators import auth_required, current_user_id

from ..api_bp import user_bank_api_bp
from ..api_shared import (
    check_bank_access,
    generate_share_code,
    get_bank_category_name,
    _parse_question_ids_from_request_args,
    _get_bank_tag_store_key,
    _load_bank_tag_store,
    _save_bank_tag_store,
)


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
            SELECT id, q_type, content, options, answer, explanation, difficulty, image_path, source_type, created_at, updated_at
            FROM user_bank_questions
            WHERE bank_id = ? AND id IN ({placeholders})
            ORDER BY sort_order ASC, id ASC
            ''',
            [bank_id, *selected_ids],
        ).fetchall()
    else:
        questions = conn.execute(
            '''
            SELECT id, q_type, content, options, answer, explanation, difficulty, image_path, source_type, created_at, updated_at
            FROM user_bank_questions
            WHERE bank_id = ?
            ORDER BY sort_order ASC, id ASC
            ''',
            (bank_id,),
        ).fetchall()

    if not questions:
        return jsonify({'code': 1, 'message': '题库中没有可导出的题目'}), 400

    items = []
    for q in questions:
        opts = []
        if q['options']:
            try:
                opts = json.loads(q['options'])
            except Exception:
                opts = []

        items.append({
            'ID': int(q['id']),
            '题型': q['q_type'] or '',
            '题干': q['content'] or '',
            '选项': opts,
            '答案': q['answer'] or '',
            '解析': q['explanation'] or '',
            '难度': int(q['difficulty'] or 1),
            '图片': q['image_path'] or '',
        })

    payload = {
        'bank': {'id': int(bank_id), 'name': bank['name']},
        'count': len(items),
        'questions': items,
    }

    export_obj = {'code': 0, **payload}

    download_flag = str(request.args.get('download') or '0').strip().lower()
    if download_flag in ('0', 'false', 'no', ''):
        return jsonify(export_obj)

    buf = io.BytesIO(json.dumps(export_obj, ensure_ascii=False, indent=2).encode('utf-8'))
    filename = f"{bank['name']}_题目导出.json"
    return send_file(
        buf,
        mimetype='application/json',
        as_attachment=True,
        download_name=filename,
    )


@user_bank_api_bp.route('/<int:bank_id>/questions/export/excel', methods=['GET'])
@auth_required
def export_questions_excel(bank_id):
    """导出题目为Excel文件"""
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
            SELECT q_type, content, options, answer, explanation, difficulty
            FROM user_bank_questions
            WHERE bank_id = ? AND id IN ({placeholders})
            ORDER BY sort_order ASC, id ASC
            ''',
            [bank_id, *selected_ids],
        ).fetchall()
    else:
        questions = conn.execute('''
            SELECT q_type, content, options, answer, explanation, difficulty
            FROM user_bank_questions
            WHERE bank_id = ?
            ORDER BY sort_order ASC, id ASC
        ''', (bank_id,)).fetchall()

    if not questions:
        return jsonify({'code': 1, 'message': '题库中没有题目'}), 400

    # 准备数据
    import json
    data = []
    max_options = 0

    for q in questions:
        opts = []
        if q['options']:
            try:
                opts = json.loads(q['options'])
            except:
                opts = []
        max_options = max(max_options, len(opts))

    for q in questions:
        row = {
            'q_type': q['q_type'],
            'content': q['content'],
            'answer': q['answer'] or '',
            'explanation': q['explanation'] or '',
            'difficulty': q['difficulty'] or 1
        }

        opts = []
        if q['options']:
            try:
                opts = json.loads(q['options'])
            except:
                opts = []

        for i in range(max_options):
            row[f'option_{i+1}'] = opts[i] if i < len(opts) else ''

        data.append(row)

    # 创建Excel
    df = pd.DataFrame(data)

    # 重排列顺序
    cols = ['q_type', 'content']
    option_cols = [f'option_{i+1}' for i in range(max_options)]
    cols.extend(option_cols)
    cols.extend(['answer', 'explanation', 'difficulty'])
    df = df.reindex(columns=cols)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='题目', index=False)

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
    """从Excel文件导入题目"""
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
        df = pd.read_excel(file).fillna('')

        # 检查必需列
        required_cols = ['q_type', 'content']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            return jsonify({'code': 1, 'message': f'Excel文件缺少必需列: {", ".join(missing)}'}), 400

        # 获取选项列
        option_cols = sorted([col for col in df.columns if col.startswith('option_')])

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
                    errors.append(f'第{idx+2}行: 选择题至少需要2个选项')
                    continue

            options_str = json.dumps(options, ensure_ascii=False) if options else None

            # 插入题目
            conn.execute('''
                INSERT INTO user_bank_questions
                (bank_id, user_id, content, q_type, options, answer, explanation, difficulty, source_type, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'custom',
                        (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = ?))
            ''', (bank_id, user_id, content, q_type, options_str, answer, explanation, difficulty, bank_id))
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
            SELECT id, q_type, content, options, answer, explanation, difficulty, image_path
            FROM user_bank_questions
            WHERE bank_id = ? AND id IN ({placeholders})
            ORDER BY sort_order ASC, id ASC
            ''',
            [bank_id, *selected_ids],
        ).fetchall()
    else:
        questions = conn.execute('''
            SELECT id, q_type, content, options, answer, explanation, difficulty, image_path
            FROM user_bank_questions
            WHERE bank_id = ?
            ORDER BY sort_order ASC, id ASC
        ''', (bank_id,)).fetchall()

    if not questions:
        return jsonify({'code': 1, 'message': '题库中没有题目'}), 400

    # 创建ZIP
    zip_buffer = io.BytesIO()
    upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, '..', 'uploads'))

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        questions_data = []
        image_count = 0

        for q in questions:
            q_data = {
                'q_type': q['q_type'],
                'content': q['content'],
                'options': json.loads(q['options']) if q['options'] else [],
                'answer': q['answer'],
                'explanation': q['explanation'],
                'difficulty': q['difficulty']
            }

            # 处理图片
            if q['image_path']:
                image_filename = os.path.basename(q['image_path'])
                full_path = os.path.join(upload_folder, q['image_path'].lstrip('/uploads/'))

                if os.path.exists(full_path):
                    new_image_name = f"images/{image_count}_{image_filename}"
                    zf.write(full_path, new_image_name)
                    q_data['image_path'] = new_image_name
                    image_count += 1

            questions_data.append(q_data)

        # 写入data.json
        zf.writestr('data.json', json.dumps(questions_data, ensure_ascii=False, indent=2))

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
                questions_data = json.load(f)

            imported_count = 0
            errors = []

            for idx, q in enumerate(questions_data):
                q_type = q.get('q_type', '').strip()
                content = q.get('content', '').strip()
                answer = q.get('answer', '')
                explanation = q.get('explanation', '')
                difficulty = q.get('difficulty', 1)
                options = q.get('options', [])

                if not q_type or not content:
                    errors.append(f'第{idx+1}题: 题型或题干为空')
                    continue

                options_str = json.dumps(options, ensure_ascii=False) if options else None

                # 处理图片
                image_path = None
                if q.get('image_path'):
                    src_image = q['image_path']
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
                conn.execute('''
                    INSERT INTO user_bank_questions
                    (bank_id, user_id, content, q_type, options, answer, explanation, difficulty, image_path, source_type, sort_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'custom',
                            (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = ?))
                ''', (bank_id, user_id, content, q_type, options_str, answer, explanation, difficulty, image_path, bank_id))
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
                    'errors': errors[:10]
                },
                'message': f'成功导入{imported_count}道题目' + (f'，{len(errors)}条错误' if errors else '')
            })

    except Exception as e:
        return jsonify({'code': 1, 'message': f'导入失败: {str(e)}'}), 500
