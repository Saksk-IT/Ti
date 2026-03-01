# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from flask import request, jsonify, session, g, current_app
from app.core.extensions import db, limiter
from sqlalchemy import text
from app.models.quiz import Favorite, Mistake
from app.models.user import User
from app.models.study import StudyLearning, StudyReview
from app.models.user_bank import UserBankMistake
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
            from app.core.utils.subject_permissions import get_user_restricted_subjects

            restricted_subject_ids = set(get_user_restricted_subjects(int(user_id))) if user_id else set()

            # 构建命名参数占位符
            id_params = {f"id_{i}": cid for i, cid in enumerate(custom_ids)}
            id_placeholders = ", ".join(f":id_{i}" for i in range(len(custom_ids)))
            rows = db.session.execute(
                text(f"""
                SELECT q.*, s.name as subject, s.is_locked as subject_is_locked,
                       CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
                       CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
                FROM questions q
                LEFT JOIN subjects s ON q.subject_id = s.id
                LEFT JOIN favorites f ON q.id = f.question_id AND f.user_id = :uid
                LEFT JOIN mistakes m ON q.id = m.question_id AND m.user_id = :uid
                WHERE q.id IN ({id_placeholders})
                """),
                {"uid": int(user_id), **id_params},
            ).fetchall()

            q_map = {int(r._mapping['id']): r for r in (rows or []) if r and r._mapping['id'] is not None}
            ordered_rows = [q_map[i] for i in custom_ids if i in q_map]

            questions = []
            for row in ordered_rows:
                try:
                    if row._mapping['subject_is_locked'] is not None and int(row._mapping['subject_is_locked']) == 1:
                        continue
                except Exception as e:
                    current_app.logger.warning(f'检查科目锁定状态失败 question_id={row._mapping.get("id")}: {e}')
                    pass

                q = Question._row_to_internal(row._mapping, scope="question_center")
                sid = q.get('subject_id')
                if sid and sid in restricted_subject_ids:
                    continue
                questions.append(q)
        else:
            query_mode = mode
            if mode not in ('favorites', 'mistakes') and source in ('favorites', 'mistakes'):
                query_mode = source

            # 提前查出 tag_ids（标签筛选下推 SQL）
            tag_ids_set = None
            if tag and str(tag).lower() != 'all':
                from app.modules.quiz.services.question_tags_service import get_question_ids_by_tag
                conn = db.session.connection()
                tag_ids_set = get_question_ids_by_tag(conn, user_id, tag)
                if not tag_ids_set:
                    return jsonify({
                        'status': 'success',
                        'data': {
                            'questions': [],
                            'total': 0,
                            'page': page,
                            'per_page': per_page,
                        }
                    }), 200

            # 权限过滤下推 SQL
            from app.core.utils.subject_permissions import get_user_accessible_subjects
            accessible_ids = get_user_accessible_subjects(int(user_id)) if user_id else None

            questions, total = Question.get_list(
                subject=subject,
                q_type=q_type,
                mode=query_mode,
                user_id=user_id,
                page=page,
                per_page=per_page,
                tag_ids=list(tag_ids_set) if tag_ids_set else None,
                accessible_subject_ids=accessible_ids,
            )
            # SQL 层已完成标签过滤和分页，无需 Python 层切片

        # 分页处理（仅 custom_ids 分支需要；SQL 分页分支已在上面完成）
        if custom_ids:
            total = len(questions)
            start = (page - 1) * per_page
            end = start + per_page
            paginated_questions = questions[start:end]
        else:
            paginated_questions = questions
        
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
        
        # 获取收藏和错题状态（ORM）
        fav_row = Favorite.query.filter_by(user_id=user_id, question_id=question_id).first()
        mistake_row = Mistake.query.filter_by(user_id=user_id, question_id=question_id).first()
        
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
@limiter.limit("10/minute")
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

    # 权限：管理员/科目管理员（ORM）
    user_obj = User.query.get(int(uid))
    if not user_obj:
        return jsonify({'status': 'error', 'message': '用户不存在'}), 404
    can_edit = bool(user_obj.is_admin) or bool(getattr(user_obj, 'is_subject_admin', False))
    if not can_edit:
        return jsonify({'status': 'forbidden', 'message': '需要管理员或科目管理员权限'}), 403

    # 读取旧题目（用于默认值/不存在校验；DB 已为 PQF 列，这里取"兼容字段"）
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
            extra = db.session.execute(
                text('SELECT difficulty, tags FROM questions WHERE id = :qid'),
                {"qid": int(question_id)},
            ).fetchone()
            if extra is not None:
                try:
                    diff_val = int(extra._mapping['difficulty'] or 1)
                except Exception as e:
                    current_app.logger.warning(f'解析题目难度失败 question_id={question_id}: {e}')
                    diff_val = 1
                tags_val = extra._mapping['tags']
        except Exception as e:
            current_app.logger.warning(f'查询题目扩展信息失败 question_id={question_id}: {e}')

        conn = db.session.connection()
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
        db.session.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f'保存失败: {str(e)}'}), 500

    # 返回更新后的题目（沿用小程序详情接口格式）
    try:
        row = db.session.execute(
            text('''
            SELECT q.*, s.name as subject
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE q.id = :qid
            '''),
            {"qid": int(question_id)},
        ).fetchone()
        if not row:
            return jsonify({'status': 'error', 'message': '题目不存在'}), 404
        q = dict(row._mapping)

        fav_row = Favorite.query.filter_by(user_id=int(uid), question_id=int(question_id)).first()
        mistake_row = Mistake.query.filter_by(user_id=int(uid), question_id=int(question_id)).first()

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
@limiter.limit("60/minute")
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

    conn = db.session.connection()
    scope_id, err = _resolve_study_scope(conn, source, subject, bank_id, uid)
    if err:
        return jsonify({'status': 'error', 'message': err}), 403

    if not _check_question_scope(conn, source, scope_id, q_id):
        return jsonify({'status': 'error', 'message': '题目不存在或不属于当前范围'}), 400

    now = now_bj()
    now_str = dt_to_str(now)

    sl_row = StudyLearning.query.filter_by(
        user_id=uid, source=source, scope_id=scope_id, question_id=q_id
    ).first()

    prev_streak = int(sl_row.streak) if sl_row and sl_row.streak is not None else 0
    prev_learned = int(sl_row.is_learned) if sl_row and sl_row.is_learned is not None else 0
    prev_correct = int(sl_row.correct_count) if sl_row and sl_row.correct_count is not None else 0
    prev_wrong = int(sl_row.wrong_count) if sl_row and sl_row.wrong_count is not None else 0

    is_correct = bool(is_correct)
    new_streak = (prev_streak + 1) if is_correct else 0
    new_learned = 1 if new_streak >= 3 else 0
    new_correct = prev_correct + (1 if is_correct else 0)
    new_wrong = prev_wrong + (0 if is_correct else 1)
    last_result = 'correct' if is_correct else 'wrong'

    if sl_row:
        sl_row.streak = new_streak
        sl_row.is_learned = bool(new_learned)
        sl_row.correct_count = new_correct
        sl_row.wrong_count = new_wrong
        sl_row.last_result = last_result
        sl_row.last_answered_at = now
        sl_row.updated_at = now
    else:
        sl_row = StudyLearning(
            user_id=uid, source=source, scope_id=scope_id, question_id=q_id,
            streak=new_streak, is_learned=bool(new_learned),
            correct_count=new_correct, wrong_count=new_wrong,
            last_result=last_result, last_answered_at=now,
            created_at=now, updated_at=now,
        )
        db.session.add(sl_row)

    # 同步维护错题本（仅记录错误）
    if not is_correct:
        if source == 'user_bank':
            ubm = UserBankMistake.query.filter_by(user_id=uid, question_id=q_id).first()
            if ubm:
                ubm.wrong_count = (ubm.wrong_count or 0) + 1
            else:
                db.session.add(UserBankMistake(
                    user_id=uid, bank_id=scope_id, question_id=q_id, wrong_count=1,
                ))
        else:
            m = Mistake.query.filter_by(user_id=uid, question_id=q_id).first()
            if m:
                m.wrong_count = (m.wrong_count or 0) + 1
            else:
                db.session.add(Mistake(
                    user_id=uid, question_id=q_id, wrong_count=1,
                ))

    next_due_str = None
    if new_learned and not prev_learned:
        due_at = next_4am(now)
        next_due_str = dt_to_str(due_at)
        review_row = StudyReview.query.filter_by(
            user_id=uid, source=source, scope_id=scope_id, question_id=q_id
        ).first()
        if review_row:
            review_row.is_mastered = False
            if review_row.next_due_at is None:
                review_row.next_due_at = due_at
            review_row.updated_at = now
        else:
            db.session.add(StudyReview(
                user_id=uid, source=source, scope_id=scope_id, question_id=q_id,
                review_level=0, next_due_at=due_at, last_review_at=None,
                last_rating=None, lapse_count=0, is_mastered=False,
                created_at=now, updated_at=now,
            ))

    db.session.commit()
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
@limiter.limit("30 per minute;300 per hour")
def study_review_summary():
    # 复习模式：查询到期题目数量
    uid = current_user_id()
    source = (request.args.get('source') or 'public').strip().lower()
    subject = request.args.get('subject')
    bank_id = request.args.get('bank_id')

    conn = db.session.connection()
    scope_id, err = _resolve_study_scope(conn, source, subject, bank_id, uid)
    if err:
        return jsonify({'status': 'error', 'message': err}), 403

    now_str = dt_to_str(now_bj())
    due_count = StudyReview.query.filter(
        StudyReview.user_id == uid,
        StudyReview.source == source,
        StudyReview.scope_id == scope_id,
        StudyReview.is_mastered == False,
        StudyReview.next_due_at.isnot(None),
        StudyReview.next_due_at <= now_str,
    ).count()
    return jsonify({'status': 'success', 'data': {'due_count': due_count}})


@quiz_api_bp.route('/study/review/record', methods=['POST'])
@auth_required
@limiter.limit("60/minute")
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

    conn = db.session.connection()
    scope_id, err = _resolve_study_scope(conn, source, subject, bank_id, uid)
    if err:
        return jsonify({'status': 'error', 'message': err}), 403

    if not _check_question_scope(conn, source, scope_id, q_id):
        return jsonify({'status': 'error', 'message': '题目不存在或不属于当前范围'}), 400

    sr_row = StudyReview.query.filter_by(
        user_id=uid, source=source, scope_id=scope_id, question_id=q_id
    ).first()

    prev_level = int(sr_row.review_level) if sr_row and sr_row.review_level is not None else 0
    prev_lapse = int(sr_row.lapse_count) if sr_row and sr_row.lapse_count is not None else 0

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

    if sr_row:
        sr_row.review_level = new_level
        sr_row.next_due_at = calc_next_due(new_level, now)
        sr_row.last_review_at = now
        sr_row.last_rating = rating
        sr_row.lapse_count = lapse
        sr_row.is_mastered = False
        sr_row.updated_at = now
    else:
        db.session.add(StudyReview(
            user_id=uid, source=source, scope_id=scope_id, question_id=q_id,
            review_level=new_level, next_due_at=calc_next_due(new_level, now),
            last_review_at=now, last_rating=rating, lapse_count=lapse,
            is_mastered=False, created_at=now, updated_at=now,
        ))

    db.session.commit()
    return jsonify({'status': 'success', 'data': {'review_level': new_level, 'next_due_at': next_due_str}})


@quiz_api_bp.route('/study/review/master', methods=['POST'])
@auth_required
@limiter.limit("30/minute")
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

    conn = db.session.connection()
    scope_id, err = _resolve_study_scope(conn, source, subject, bank_id, uid)
    if err:
        return jsonify({'status': 'error', 'message': err}), 403

    if not _check_question_scope(conn, source, scope_id, q_id):
        return jsonify({'status': 'error', 'message': '题目不存在或不属于当前范围'}), 400

    now = now_bj()
    now_str = dt_to_str(now)
    mastered = 1 if bool(is_mastered) else 0

    sr_row = StudyReview.query.filter_by(
        user_id=uid, source=source, scope_id=scope_id, question_id=q_id
    ).first()

    next_due_dt = None if mastered else next_4am(now)

    if sr_row:
        sr_row.is_mastered = bool(mastered)
        sr_row.next_due_at = next_due_dt
        sr_row.updated_at = now
    else:
        db.session.add(StudyReview(
            user_id=uid, source=source, scope_id=scope_id, question_id=q_id,
            review_level=0, next_due_at=next_due_dt, last_review_at=None,
            last_rating=None, lapse_count=0, is_mastered=bool(mastered),
            created_at=now, updated_at=now,
        ))

    db.session.commit()
    return jsonify({'status': 'success', 'data': {'is_mastered': mastered}})
