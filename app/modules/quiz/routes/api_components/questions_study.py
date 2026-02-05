# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from flask import request, jsonify, session, g, current_app
from app.core.utils.database import get_db
from app.core.extensions import limiter
from app.core.utils.decorators import jwt_required, auth_required, current_user_id
from app.core.utils.redis_utils import redis_get_json, redis_set_json
from app.core.utils.cache_utils import (
    bump_questions_version,
    bump_user_quiz_version,
    get_questions_version,
    get_subjects_version,
    get_user_quiz_version,
    make_cache_key,
)
from typing import Optional
from app.core.models.question import Question
from app.core.utils.options_parser import parse_options
from app.modules.quiz.services.study_service import now_bj, dt_to_str, next_4am, calc_next_due, clamp_level
from app.modules.quiz.services.reinforcement_service import (
    find_similar_pairs_public,
    find_similar_pairs_user_bank,
    find_similar_training_ids_public,
    find_similar_training_ids_user_bank,
)

from ..api_bp import quiz_api_bp
from ..api_shared import _get_uid_from_request, _resolve_study_scope, _check_question_scope


def _parse_id_list(val, max_len: int = 200):
    if not val:
        return []
    try:
        s = str(val)
    except Exception:
        return []
    s = s.replace("，", ",").strip()
    if not s:
        return []
    parts = [p.strip() for p in s.split(",") if p.strip()]
    out = []
    seen = set()
    for p in parts:
        if len(out) >= max_len:
            break
        try:
            n = int(p)
        except Exception:
            continue
        if n <= 0:
            continue
        if n in seen:
            continue
        seen.add(n)
        out.append(n)
    return out


@quiz_api_bp.route('/questions', methods=['GET'])
@jwt_required
def api_get_questions():
    """获取题目列表（JSON格式，用于小程序）"""
    try:
        # 获取查询参数
        subject = request.args.get('subject', 'all')
        q_type = request.args.get('q_type', 'all')
        mode = (request.args.get('mode', 'quiz') or 'quiz').lower()
        source = (request.args.get('source') or '').strip().lower()
        tag = (request.args.get('tag') or '').strip()
        shuffle_options = request.args.get('shuffle_options', '0') in ('1', 'true', 'True')
        page = request.args.get('page', 1, type=int)
        # 小程序刷题页支持一次性加载较多题目（用于离线/顺滑切题）
        per_page = min(request.args.get('per_page', 20, type=int), 1000)
        
        # 从JWT token获取用户ID
        user_id = g.current_user_id
        
        # 获取题目列表
        # 兼容：小程序用 source=all/favorites/mistakes；旧逻辑也允许 mode=favorites/mistakes
        custom_ids = _parse_id_list(request.args.get('ids') or request.args.get('question_ids'))
        if custom_ids:
            conn = get_db()
            from app.core.utils.subject_permissions import get_user_restricted_subjects

            restricted_subject_ids = set(get_user_restricted_subjects(int(user_id))) if user_id else set()

            placeholders = ",".join(["?"] * len(custom_ids))
            rows = conn.execute(
                f"""
                SELECT q.*, s.name as subject, s.is_locked as subject_is_locked,
                       CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
                       CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
                FROM questions q
                LEFT JOIN subjects s ON q.subject_id = s.id
                LEFT JOIN favorites f ON q.id = f.question_id AND f.user_id = ?
                LEFT JOIN mistakes m ON q.id = m.question_id AND m.user_id = ?
                WHERE q.id IN ({placeholders})
                """,
                [int(user_id), int(user_id)] + list(custom_ids),
            ).fetchall()

            q_map = {int(r['id']): r for r in (rows or []) if r and r['id'] is not None}
            ordered_rows = [q_map[i] for i in custom_ids if i in q_map]

            questions = []
            for row in ordered_rows:
                try:
                    if row['subject_is_locked'] is not None and int(row['subject_is_locked']) == 1:
                        continue
                except Exception:
                    pass

                q = Question._row_to_internal(row, scope="question_center")
                sid = q.get('subject_id')
                if sid and sid in restricted_subject_ids:
                    continue
                questions.append(q)
        else:
            query_mode = mode
            if mode not in ('favorites', 'mistakes') and source in ('favorites', 'mistakes'):
                query_mode = source
            questions = Question.get_list(
                subject=subject,
                q_type=q_type,
                mode=query_mode,
                user_id=user_id
            )

        # 标签筛选（用户私有）
        if tag and str(tag).lower() != 'all':
            from app.modules.quiz.services.question_tags_service import get_question_ids_by_tag
            conn = get_db()
            tag_ids = get_question_ids_by_tag(conn, user_id, tag)
            if not tag_ids:
                questions = []
            else:
                questions = [q for q in questions if int(q.get('id') or 0) in tag_ids]
        
        # 分页处理
        total = len(questions)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_questions = questions[start:end]
        
        # 格式化题目数据（转换为小程序需要的格式）
        formatted_questions = []
        for q in paginated_questions:
            q_type_val = q.get('q_type', '')
            options = parse_options(q.get('options'))
            # 判断题历史数据常为 []，小程序端需要可选项用于作答
            if q_type_val == '判断题' and not options:
                options = [
                    {'key': '正确', 'value': '正确'},
                    {'key': '错误', 'value': '错误'},
                ]

            # 打乱选项（确定性随机，与 Web 端保持一致；会同步重算答案字母）
            answer = q.get('answer', '') or ''
            if shuffle_options and options and q_type_val in ('选择题', '多选题'):
                try:
                    import random

                    orig_answer_keys = str(answer)
                    options_map = {opt.get('key'): opt.get('value') for opt in options}
                    correct_texts = []
                    for key in orig_answer_keys:
                        if key in options_map:
                            correct_texts.append(options_map[key])

                    shuffle_seed = int(user_id) * 1000000 + int(q.get('id') or 0)
                    rng = random.Random(shuffle_seed)
                    rng.shuffle(options)

                    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                    new_answer_keys = []
                    for i, option in enumerate(options):
                        if i < len(letters):
                            option['key'] = letters[i]
                            if option.get('value') in correct_texts:
                                new_answer_keys.append(option['key'])

                    answer = ''.join(sorted(new_answer_keys))
                except Exception:
                    # 选项打乱失败时兜底：保持原 options/answer
                    pass
            
            formatted_q = {
                'id': q.get('id'),
                'content': q.get('content', ''),
                'q_type': q_type_val,
                'options': options,
                'answer': answer,
                'explanation': q.get('explanation', ''),
                'image_path': q.get('image_path'),
                'subject': q.get('subject', ''),
                'is_fav': q.get('is_fav', 0),
                'is_mistake': q.get('is_mistake', 0)
            }
            formatted_questions.append(formatted_q)
        
        return jsonify({
            'status': 'success',
            'data': {
                'questions': formatted_questions,
                'total': total,
                'page': page,
                'per_page': per_page
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'获取题目列表失败: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'获取题目列表失败: {str(e)}'
        }), 500


@quiz_api_bp.route('/questions/<int:question_id>', methods=['GET'])
@auth_required
def api_get_question_detail(question_id):
    """获取题目详情（JSON格式，Web/小程序通用）"""
    try:
        shuffle_options = request.args.get('shuffle_options', '0') in ('1', 'true', 'True')
        # 从JWT token或session获取用户ID
        user_id = g.current_user_id

        cache_key = None
        if bool(current_app.config.get('QUIZ_API_CACHE_ENABLED', True)):
            try:
                cache_key = make_cache_key(
                    'quiz:question_detail',
                    {
                        'qid': int(question_id),
                        'uid': int(user_id),
                        'shuffle': 1 if shuffle_options else 0,
                        'uv': get_user_quiz_version(int(user_id)),
                        'qv': get_questions_version(),
                        'sv': get_subjects_version(),
                    },
                )
                cached = redis_get_json(cache_key)
                if isinstance(cached, dict) and cached.get('status') == 'success' and 'data' in cached:
                    return jsonify(cached), 200
            except Exception:
                cache_key = None
        
        # 获取题目详情
        question = Question.get_by_id(question_id)
        if not question:
            return jsonify({
                'status': 'error',
                'message': '题目不存在'
            }), 404
        
        # 检查用户权限（通过科目权限过滤）
        from app.core.utils.subject_permissions import can_user_access_subject
        if question.get('subject_id') and not can_user_access_subject(user_id, question['subject_id']):
            return jsonify({
                'status': 'error',
                'message': '无权限访问该题目'
            }), 403
        
        # 获取收藏和错题状态
        conn = get_db()
        fav_row = conn.execute(
            'SELECT id FROM favorites WHERE user_id = ? AND question_id = ?',
            (user_id, question_id)
        ).fetchone()
        mistake_row = conn.execute(
            'SELECT id FROM mistakes WHERE user_id = ? AND question_id = ?',
            (user_id, question_id)
        ).fetchone()
        
        q_type_val = question.get('q_type', '')
        options = parse_options(question.get('options'))
        if q_type_val == '判断题' and not options:
            options = [
                {'key': '正确', 'value': '正确'},
                {'key': '错误', 'value': '错误'},
            ]

        answer = question.get('answer', '') or ''
        if shuffle_options and options and q_type_val in ('选择题', '多选题'):
            try:
                import random

                orig_answer_keys = str(answer)
                options_map = {opt.get('key'): opt.get('value') for opt in options}
                correct_texts = []
                for key in orig_answer_keys:
                    if key in options_map:
                        correct_texts.append(options_map[key])

                shuffle_seed = int(user_id) * 1000000 + int(question_id)
                rng = random.Random(shuffle_seed)
                rng.shuffle(options)

                letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                new_answer_keys = []
                for i, option in enumerate(options):
                    if i < len(letters):
                        option['key'] = letters[i]
                        if option.get('value') in correct_texts:
                            new_answer_keys.append(option['key'])

                answer = ''.join(sorted(new_answer_keys))
            except Exception:
                pass
        
        # 格式化题目数据
        formatted_question = {
            'id': question.get('id'),
            'content': question.get('content', ''),
            'q_type': q_type_val,
            'options': options,
            'answer': answer,
            'explanation': question.get('explanation', ''),
            'image_path': question.get('image_path'),
            'subject': question.get('subject', ''),
            'is_fav': 1 if fav_row else 0,
            'is_mistake': 1 if mistake_row else 0
        }

        payload = {'status': 'success', 'data': formatted_question}
        if cache_key and bool(current_app.config.get('QUIZ_API_CACHE_ENABLED', True)):
            try:
                ttl = int(current_app.config.get('QUIZ_CACHE_TTL_QUESTION_DETAIL_SECONDS', 300) or 300)
            except Exception:
                ttl = 300
            if ttl > 0:
                redis_set_json(cache_key, payload, ttl_seconds=ttl)

        return jsonify(payload), 200
        
    except Exception as e:
        current_app.logger.error(f'获取题目详情失败: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'获取题目详情失败: {str(e)}'
        }), 500


@quiz_api_bp.route('/questions/<int:question_id>', methods=['PUT'])
@auth_required  # 支持 session 和 JWT
@limiter.exempt
def api_update_question(question_id: int):
    """编辑题目（管理员/科目管理员：答题页内弹窗编辑）"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    data = request.json or {}
    content = data.get('content')
    q_type = data.get('q_type')
    answer = data.get('answer')
    explanation = data.get('explanation')
    options_in = data.get('options', None)

    # 基础校验
    if content is not None and not isinstance(content, str):
        return jsonify({'status': 'error', 'message': 'content 必须为字符串'}), 400
    if q_type is not None and not isinstance(q_type, str):
        return jsonify({'status': 'error', 'message': 'q_type 必须为字符串'}), 400
    if answer is not None and not isinstance(answer, str):
        return jsonify({'status': 'error', 'message': 'answer 必须为字符串'}), 400
    if explanation is not None and not isinstance(explanation, str):
        return jsonify({'status': 'error', 'message': 'explanation 必须为字符串'}), 400

    conn = get_db()

    # 权限：管理员/科目管理员
    try:
        user_cols = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    except Exception:
        user_cols = []
    role_fields = ['is_admin']
    if 'is_subject_admin' in user_cols:
        role_fields.append('is_subject_admin')
    role_row = conn.execute(
        f"SELECT {', '.join(role_fields)} FROM users WHERE id = ?",
        (int(uid),)
    ).fetchone()
    if not role_row:
        return jsonify({'status': 'error', 'message': '用户不存在'}), 404
    role_row = dict(role_row)
    can_edit = bool(role_row.get('is_admin')) or bool(role_row.get('is_subject_admin'))
    if not can_edit:
        return jsonify({'status': 'forbidden', 'message': '需要管理员或科目管理员权限'}), 403

    # 读取旧题目（用于默认值/不存在校验；DB 已为 PQF 列，这里取“兼容字段”）
    old = Question.get_by_id(int(question_id))
    if not old:
        return jsonify({'status': 'error', 'message': '题目不存在'}), 404

    next_q_type = (q_type if q_type is not None else (old.get('q_type') or '')).strip()
    next_content = (content if content is not None else (old.get('content') or '')).strip()
    next_answer = (answer if answer is not None else (old.get('answer') or '')).strip()
    next_explanation = (explanation if explanation is not None else (old.get('explanation') or '')).strip()

    # options：允许数组/对象（前端结构化）或字符串（JSON/纯文本）
    options_str = None
    options_list = None
    if options_in is None:
        options_str = old.get('options')
        options_list = old.get('options')
    else:
        if isinstance(options_in, str):
            options_str = options_in
            options_list = options_in
        else:
            try:
                import json
                options_str = json.dumps(options_in, ensure_ascii=False)
                options_list = options_in
            except Exception:
                return jsonify({'status': 'error', 'message': 'options 格式错误'}), 400

    # 多选题校验：答案至少两个选项，且必须在选项范围内
    if next_q_type == '多选题':
        if len(next_answer) < 2:
            return jsonify({'status': 'error', 'message': '多选题答案至少需要两个选项，例如：AB 或 ABC'}), 400
        try:
            import json
            options_parsed = options_list
            if isinstance(options_parsed, str):
                options_parsed = json.loads(options_parsed) if options_parsed.strip() else []
            parsed_options = parse_options(options_parsed)
            valid_keys = {opt.get('key') for opt in parsed_options if opt.get('key')}
            answer_keys = set(next_answer.upper())
            invalid_keys = answer_keys - valid_keys
            if invalid_keys:
                return jsonify({
                    'status': 'error',
                    'message': f'多选题答案中包含无效选项：{", ".join(sorted(invalid_keys))}。有效选项为：{", ".join(sorted(valid_keys))}'
                }), 400
        except Exception:
            # 解析失败时不阻塞（保持兼容旧数据），由题库管理页进一步校验
            pass

    try:
        from app.core.utils.portable_question_sync import try_sync_questions_portable_columns

        diff_val = 1
        tags_val = None
        try:
            extra = conn.execute(
                'SELECT difficulty, tags FROM questions WHERE id = ?',
                (int(question_id),),
            ).fetchone()
            if extra is not None:
                try:
                    diff_val = int(extra['difficulty'] or 1)
                except Exception:
                    diff_val = 1
                tags_val = extra['tags']
        except Exception:
            pass

        try_sync_questions_portable_columns(
            conn,
            question_id=int(question_id),
            q_type=next_q_type,
            content=next_content,
            options=options_str,
            answer=next_answer,
            explanation=next_explanation,
            difficulty=diff_val,
            tags=tags_val,
        )
        conn.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': f'保存失败: {str(e)}'}), 500

    # 返回更新后的题目（沿用小程序详情接口格式）
    try:
        row = conn.execute(
            '''
            SELECT q.*, s.name as subject
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE q.id = ?
            ''',
            (int(question_id),)
        ).fetchone()
        if not row:
            return jsonify({'status': 'error', 'message': '题目不存在'}), 404
        q = dict(row)

        fav_row = conn.execute(
            'SELECT id FROM favorites WHERE user_id = ? AND question_id = ?',
            (int(uid), int(question_id))
        ).fetchone()
        mistake_row = conn.execute(
            'SELECT id FROM mistakes WHERE user_id = ? AND question_id = ?',
            (int(uid), int(question_id))
        ).fetchone()

        # DB 已为 PQF 列：把 type/content/options/answer/analysis 转成旧字段（q_type/答案字符串/填空 __）
        from app.core.utils.portable_question_format import portable_question_to_internal
        import json as _json

        portable = {
            "id": int(q.get("id") or 0),
            "type": q.get("type") or "",
            "content": q.get("content") or "",
            "options": (_json.loads(q.get("options") or "[]") if isinstance(q.get("options"), str) else (q.get("options") or [])),
            "answer": (_json.loads(q.get("answer") or "[]") if isinstance(q.get("answer"), str) else (q.get("answer") or [])),
            "analysis": q.get("analysis") or "",
            "tags": (_json.loads(q.get("tags") or "[]") if isinstance(q.get("tags"), str) else (q.get("tags") or [])),
            "difficulty": q.get("difficulty") if q.get("difficulty") is not None else 1,
        }
        internal, _errors = portable_question_to_internal(portable, scope="question_center")

        q_type_val = internal.get('q_type', '')
        options = parse_options(internal.get('options'))
        if q_type_val == '判断题' and not options:
            options = [
                {'key': '正确', 'value': '正确'},
                {'key': '错误', 'value': '错误'},
            ]

        formatted_question = {
            'id': q.get('id'),
            'content': internal.get('content', '') or q.get('content', ''),
            'q_type': q_type_val,
            'options': options,
            'answer': internal.get('answer', '') or '',
            'explanation': internal.get('explanation', ''),
            'image_path': q.get('image_path'),
            'subject': q.get('subject', '') or '',
            'is_fav': 1 if fav_row else 0,
            'is_mistake': 1 if mistake_row else 0
        }

        return jsonify({'status': 'success', 'data': formatted_question}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'题目更新成功但返回数据失败: {str(e)}'}), 500



@quiz_api_bp.route('/study/learn/record', methods=['POST'])
@auth_required
@limiter.exempt
def study_learn_record():
    # 学习模式：记录答题结果
    data = request.get_json(silent=True) or {}
    uid = current_user_id()
    q_id = data.get('question_id')
    is_correct = data.get('is_correct')
    source = (data.get('source') or 'public').strip().lower()
    subject = data.get('subject')
    bank_id = data.get('bank_id')

    try:
        q_id = int(q_id)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'question_id 参数错误'}), 400

    if is_correct is None:
        return jsonify({'status': 'error', 'message': 'is_correct 参数错误'}), 400

    conn = get_db()
    scope_id, err = _resolve_study_scope(conn, source, subject, bank_id, uid)
    if err:
        return jsonify({'status': 'error', 'message': err}), 403

    if not _check_question_scope(conn, source, scope_id, q_id):
        return jsonify({'status': 'error', 'message': '题目不存在或不属于当前范围'}), 400

    now = now_bj()
    now_str = dt_to_str(now)

    row = conn.execute(
        """SELECT streak, is_learned, correct_count, wrong_count
           FROM study_learning
           WHERE user_id = ? AND source = ? AND scope_id = ? AND question_id = ?""",
        (uid, source, scope_id, q_id),
    ).fetchone()

    prev_streak = int(row['streak']) if row and row['streak'] is not None else 0
    prev_learned = int(row['is_learned']) if row and row['is_learned'] is not None else 0
    prev_correct = int(row['correct_count']) if row and row['correct_count'] is not None else 0
    prev_wrong = int(row['wrong_count']) if row and row['wrong_count'] is not None else 0

    is_correct = bool(is_correct)
    new_streak = (prev_streak + 1) if is_correct else 0
    new_learned = 1 if new_streak >= 3 else 0
    new_correct = prev_correct + (1 if is_correct else 0)
    new_wrong = prev_wrong + (0 if is_correct else 1)
    last_result = 'correct' if is_correct else 'wrong'

    if row:
        conn.execute(
            """UPDATE study_learning
               SET streak = ?, is_learned = ?, correct_count = ?, wrong_count = ?,
                   last_result = ?, last_answered_at = ?, updated_at = ?
               WHERE user_id = ? AND source = ? AND scope_id = ? AND question_id = ?""",
            (new_streak, new_learned, new_correct, new_wrong, last_result, now_str, now_str, uid, source, scope_id, q_id),
        )
    else:
        conn.execute(
            """INSERT INTO study_learning
               (user_id, source, scope_id, question_id, streak, is_learned, correct_count, wrong_count, last_result, last_answered_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (uid, source, scope_id, q_id, new_streak, new_learned, new_correct, new_wrong, last_result, now_str, now_str, now_str),
        )

    # 同步维护错题本（仅记录错误）
    if not is_correct:
        try:
            if source == 'user_bank':
                conn.execute(
                    """INSERT INTO user_bank_mistakes (user_id, bank_id, question_id, wrong_count, created_at, updated_at)
                       VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                       ON CONFLICT(user_id, question_id) DO UPDATE SET
                         wrong_count = wrong_count + 1,
                         updated_at = CURRENT_TIMESTAMP""",
                    (uid, scope_id, q_id),
                )
            else:
                conn.execute(
                    """INSERT INTO mistakes (user_id, question_id, wrong_count, created_at, updated_at, last_updated)
                       VALUES (?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                       ON CONFLICT(user_id, question_id) DO UPDATE SET
                         wrong_count = wrong_count + 1,
                         updated_at = CURRENT_TIMESTAMP,
                         last_updated = CURRENT_TIMESTAMP""",
                    (uid, q_id),
                )
        except Exception:
            if source == 'user_bank':
                conn.execute(
                    "INSERT INTO user_bank_mistakes (user_id, bank_id, question_id, wrong_count) VALUES (?, ?, ?, 1) ON CONFLICT(user_id, question_id) DO UPDATE SET wrong_count = wrong_count + 1",
                    (uid, scope_id, q_id),
                )
            else:
                conn.execute(
                    "INSERT INTO mistakes (user_id, question_id, wrong_count) VALUES (?, ?, 1) ON CONFLICT(user_id, question_id) DO UPDATE SET wrong_count = wrong_count + 1",
                    (uid, q_id),
                )

    next_due_str = None
    if new_learned and not prev_learned:
        due_at = next_4am(now)
        next_due_str = dt_to_str(due_at)
        review_row = conn.execute(
            """SELECT id, is_mastered, next_due_at, review_level
               FROM study_review
               WHERE user_id = ? AND source = ? AND scope_id = ? AND question_id = ?""",
            (uid, source, scope_id, q_id),
        ).fetchone()
        if review_row:
            conn.execute(
                """UPDATE study_review
                   SET is_mastered = 0,
                       next_due_at = COALESCE(next_due_at, ?),
                       updated_at = ?
                   WHERE user_id = ? AND source = ? AND scope_id = ? AND question_id = ?""",
                (next_due_str, now_str, uid, source, scope_id, q_id),
            )
        else:
            conn.execute(
                """INSERT INTO study_review
                   (user_id, source, scope_id, question_id, review_level, next_due_at, last_review_at, last_rating, lapse_count, is_mastered, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 0, ?, NULL, NULL, 0, 0, ?, ?)""",
                (uid, source, scope_id, q_id, next_due_str, now_str, now_str),
            )

    conn.commit()
    try:
        bump_user_quiz_version(int(uid))
    except Exception:
        pass
    return jsonify({
        'status': 'success',
        'data': {
            'streak': new_streak,
            'is_learned': new_learned,
            'next_due_at': next_due_str
        }
    })


@quiz_api_bp.route('/study/review/summary')
@auth_required
@limiter.exempt
def study_review_summary():
    # 复习模式：查询到期题目数量
    uid = current_user_id()
    source = (request.args.get('source') or 'public').strip().lower()
    subject = request.args.get('subject')
    bank_id = request.args.get('bank_id')

    conn = get_db()
    scope_id, err = _resolve_study_scope(conn, source, subject, bank_id, uid)
    if err:
        return jsonify({'status': 'error', 'message': err}), 403

    now_str = dt_to_str(now_bj())
    row = conn.execute(
        """SELECT COUNT(1) AS cnt
           FROM study_review
           WHERE user_id = ? AND source = ? AND scope_id = ?
             AND is_mastered = 0
             AND next_due_at IS NOT NULL
             AND next_due_at <= ?""",
        (uid, source, scope_id, now_str),
    ).fetchone()
    due_count = int(row['cnt']) if row else 0
    return jsonify({'status': 'success', 'data': {'due_count': due_count}})


@quiz_api_bp.route('/study/review/record', methods=['POST'])
@auth_required
@limiter.exempt
def study_review_record():
    # 复习模式：记录评分（known/fuzzy/unknown）
    data = request.get_json(silent=True) or {}
    uid = current_user_id()
    q_id = data.get('question_id')
    rating = (data.get('rating') or '').strip().lower()
    source = (data.get('source') or 'public').strip().lower()
    subject = data.get('subject')
    bank_id = data.get('bank_id')

    if rating not in ('known', 'fuzzy', 'unknown'):
        return jsonify({'status': 'error', 'message': 'rating 参数错误'}), 400

    try:
        q_id = int(q_id)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'question_id 参数错误'}), 400

    conn = get_db()
    scope_id, err = _resolve_study_scope(conn, source, subject, bank_id, uid)
    if err:
        return jsonify({'status': 'error', 'message': err}), 403

    if not _check_question_scope(conn, source, scope_id, q_id):
        return jsonify({'status': 'error', 'message': '题目不存在或不属于当前范围'}), 400

    row = conn.execute(
        """SELECT review_level, lapse_count
           FROM study_review
           WHERE user_id = ? AND source = ? AND scope_id = ? AND question_id = ?""",
        (uid, source, scope_id, q_id),
    ).fetchone()

    prev_level = int(row['review_level']) if row and row['review_level'] is not None else 0
    prev_lapse = int(row['lapse_count']) if row and row['lapse_count'] is not None else 0

    if rating == 'known':
        new_level = clamp_level(prev_level + 1)
        lapse = prev_lapse
    elif rating == 'fuzzy':
        new_level = clamp_level(prev_level - 1)
        lapse = prev_lapse
    else:
        new_level = 0
        lapse = prev_lapse + 1

    now = now_bj()
    now_str = dt_to_str(now)
    next_due_str = dt_to_str(calc_next_due(new_level, now))

    if row:
        conn.execute(
            """UPDATE study_review
               SET review_level = ?, next_due_at = ?, last_review_at = ?, last_rating = ?,
                   lapse_count = ?, is_mastered = 0, updated_at = ?
               WHERE user_id = ? AND source = ? AND scope_id = ? AND question_id = ?""",
            (new_level, next_due_str, now_str, rating, lapse, now_str, uid, source, scope_id, q_id),
        )
    else:
        conn.execute(
            """INSERT INTO study_review
               (user_id, source, scope_id, question_id, review_level, next_due_at, last_review_at, last_rating, lapse_count, is_mastered, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
            (uid, source, scope_id, q_id, new_level, next_due_str, now_str, rating, lapse, now_str, now_str),
        )

    conn.commit()
    return jsonify({'status': 'success', 'data': {'review_level': new_level, 'next_due_at': next_due_str}})


@quiz_api_bp.route('/study/review/master', methods=['POST'])
@auth_required
@limiter.exempt
def study_review_master():
    # 标记掌握/取消掌握
    data = request.get_json(silent=True) or {}
    uid = current_user_id()
    q_id = data.get('question_id')
    is_mastered = data.get('is_mastered', True)
    source = (data.get('source') or 'public').strip().lower()
    subject = data.get('subject')
    bank_id = data.get('bank_id')

    try:
        q_id = int(q_id)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'question_id 参数错误'}), 400

    conn = get_db()
    scope_id, err = _resolve_study_scope(conn, source, subject, bank_id, uid)
    if err:
        return jsonify({'status': 'error', 'message': err}), 403

    if not _check_question_scope(conn, source, scope_id, q_id):
        return jsonify({'status': 'error', 'message': '题目不存在或不属于当前范围'}), 400

    now = now_bj()
    now_str = dt_to_str(now)
    mastered = 1 if bool(is_mastered) else 0
    next_due_str = None if mastered else dt_to_str(next_4am(now))

    row = conn.execute(
        """SELECT id FROM study_review
           WHERE user_id = ? AND source = ? AND scope_id = ? AND question_id = ?""",
        (uid, source, scope_id, q_id),
    ).fetchone()

    if row:
        conn.execute(
            """UPDATE study_review
               SET is_mastered = ?, next_due_at = ?, updated_at = ?
               WHERE user_id = ? AND source = ? AND scope_id = ? AND question_id = ?""",
            (mastered, next_due_str, now_str, uid, source, scope_id, q_id),
        )
    else:
        conn.execute(
            """INSERT INTO study_review
               (user_id, source, scope_id, question_id, review_level, next_due_at, last_review_at, last_rating, lapse_count, is_mastered, created_at, updated_at)
               VALUES (?, ?, ?, ?, 0, ?, NULL, NULL, 0, ?, ?, ?)""",
            (uid, source, scope_id, q_id, next_due_str, mastered, now_str, now_str),
        )

    conn.commit()
    return jsonify({'status': 'success', 'data': {'is_mastered': mastered}})
