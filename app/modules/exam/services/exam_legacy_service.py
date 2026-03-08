# -*- coding: utf-8 -*-
"""
考试遗留业务服务

从 app/core/models/exam.py 迁移而来，集中考试相关的数据库操作与业务规则。
类名从 Exam 改为 ExamLegacyService，保留向后兼容别名 Exam。
"""
import json
from datetime import datetime
from app.core.extensions import db
from app.core.utils.json_helpers import safe_json_load
from sqlalchemy import text


class ExamLegacyService:
    """考试遗留业务服务（集中与考试相关的数据库操作与业务规则）"""

    @staticmethod
    def _normalize_subject(subject):
        s = (subject or 'all').strip()
        return s if s else 'all'

    @staticmethod
    def _safe_int(v, default=0, min_v=None, max_v=None):
        try:
            iv = int(v)
        except Exception:
            iv = int(default)
        if min_v is not None:
            iv = max(min_v, iv)
        if max_v is not None:
            iv = min(max_v, iv)
        return iv

    @staticmethod
    def _safe_float(v, default=0.0, min_v=None, max_v=None):
        try:
            fv = float(v)
        except Exception:
            fv = float(default)
        if min_v is not None:
            fv = max(min_v, fv)
        if max_v is not None:
            fv = min(max_v, fv)
        return fv

    @staticmethod
    def _parse_config_json(config_json: str) -> dict:
        try:
            cfg = json.loads(config_json or '{}')
            return cfg if isinstance(cfg, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _normalize_source(source: str) -> str:
        s = (source or 'public').strip().lower()
        return s if s in ('public', 'user_bank') else 'public'

    @staticmethod
    def create(user_id, subject, duration, types_config, scores_config, source: str = 'public', bank_id=None, grading_mode: str = 'auto_full'):
        """创建考试：写入 exams + exam_questions，并返回 exam_id

        规则：
        - subject='all' 表示不限制科目
        - types_config: {题型: 题数}
        - scores_config: {题型: 分值}
        """
        subject = ExamLegacyService._normalize_subject(subject)
        source = ExamLegacyService._normalize_source(source)
        duration = ExamLegacyService._safe_int(duration, default=60, min_v=1, max_v=24 * 60)
        types_config = types_config or {}
        scores_config = scores_config or {}

        config_payload = {
            'subject': subject,
            'duration': duration,
            'types': types_config,
            'scores': scores_config,
            'source': source,
            'grading_mode': grading_mode,
        }
        if source == 'user_bank':
            try:
                bank_id_int = int(bank_id)
            except Exception:
                bank_id_int = 0
            if bank_id_int <= 0:
                raise ValueError('invalid bank_id')
            config_payload['bank_id'] = bank_id_int

        config_json = json.dumps(config_payload, ensure_ascii=False)

        result = db.session.execute(
            text('INSERT INTO exams (user_id, subject, duration_minutes, config_json, status) VALUES (:user_id, :subject, :duration, :config_json, :status) RETURNING id'),
            {'user_id': user_id, 'subject': subject, 'duration': duration, 'config_json': config_json, 'status': 'ongoing'}
        )
        exam_id = result.scalar()

        order_index = 0
        sub_sql = " AND s.name = :subject_name" if subject != 'all' else ""
        sub_params_extra = {'subject_name': subject} if subject != 'all' else {}

        from app.core.utils.portable_question_format import any_type_to_portable_type

        for q_type, count in (types_config or {}).items():
            cnt = ExamLegacyService._safe_int(count, default=0, min_v=0, max_v=500)
            if cnt <= 0:
                continue
            portable_type = any_type_to_portable_type(q_type)

            if source == 'user_bank':
                sql = text(
                    "SELECT q.* FROM user_bank_questions q "
                    "WHERE q.bank_id = :bank_id AND q.type = :ptype "
                    "ORDER BY RANDOM() LIMIT :cnt"
                )
                params = {'bank_id': config_payload.get('bank_id'), 'ptype': portable_type, 'cnt': cnt}
                rows = db.session.execute(sql, params).fetchall()
            else:
                sql = text(
                    "SELECT q.* FROM questions q "
                    "LEFT JOIN subjects s ON q.subject_id = s.id "
                    f"WHERE q.type = :ptype{sub_sql} "
                    "ORDER BY RANDOM() LIMIT :cnt"
                )
                params = {'ptype': portable_type, 'cnt': cnt, **sub_params_extra}
                rows = db.session.execute(sql, params).fetchall()

            for row in rows:
                score_val = ExamLegacyService._safe_float(scores_config.get(q_type, 1), default=1.0, min_v=0.0, max_v=1000.0)
                db.session.execute(
                    text('INSERT INTO exam_questions (exam_id, question_id, order_index, score_val) VALUES (:exam_id, :question_id, :order_index, :score_val)'),
                    {'exam_id': exam_id, 'question_id': row._mapping['id'], 'order_index': order_index, 'score_val': score_val}
                )
                order_index += 1

        db.session.commit()
        return exam_id

    @staticmethod
    def get_by_id(exam_id, user_id=None):
        """获取考试与题目（含用户作答与判分字段）"""
        exam_row = db.session.execute(
            text('SELECT * FROM exams WHERE id=:exam_id'), {'exam_id': exam_id}
        ).fetchone()

        if not exam_row:
            return None

        exam = dict(exam_row._mapping)

        if user_id and exam['user_id'] != user_id:
            return None

        cfg = ExamLegacyService._parse_config_json(exam.get('config_json'))
        source = ExamLegacyService._normalize_source(cfg.get('source'))

        if source == 'user_bank':
            rows = db.session.execute(
                text("""
                SELECT q.*, eq.score_val, eq.order_index, eq.user_answer, eq.is_correct
                FROM exam_questions eq
                JOIN user_bank_questions q ON q.id = eq.question_id
                WHERE eq.exam_id=:exam_id
                ORDER BY eq.order_index
                """),
                {'exam_id': exam_id},
            ).fetchall()
        else:
            rows = db.session.execute(
                text("""
                SELECT q.*, eq.score_val, eq.order_index, eq.user_answer, eq.is_correct
                FROM exam_questions eq
                JOIN questions q ON q.id = eq.question_id
                WHERE eq.exam_id=:exam_id
                ORDER BY eq.order_index
                """),
                {'exam_id': exam_id},
            ).fetchall()

        from app.core.utils.portable_question_format import portable_question_to_internal

        scope = "user_bank" if source == "user_bank" else "question_center"
        out = []
        for r in rows or []:
            d = dict(r._mapping)
            portable = {
                "id": d.get("id"),
                "type": d.get("type") or "",
                "content": d.get("content") or "",
                "options": safe_json_load(d.get("options"), []),
                "answer": safe_json_load(d.get("answer"), []),
                "analysis": d.get("analysis") or "",
                "tags": safe_json_load(d.get("tags"), []),
                "difficulty": d.get("difficulty") if d.get("difficulty") is not None else 1,
            }
            internal, _errors = portable_question_to_internal(portable, scope=scope)
            d["q_type"] = internal.get("q_type") or ""
            d["content"] = internal.get("content") or ""
            d["options"] = internal.get("options") or []
            d["answer"] = internal.get("answer") or ""
            d["explanation"] = internal.get("explanation") or ""
            out.append(d)

        return {'exam': exam, 'questions': out}

    @staticmethod
    def _grade_answer(q_type, user_ans, std_ans):
        q_type = (q_type or '').strip()
        user_ans = (user_ans or '').strip()
        std_ans = (std_ans or '').strip()

        if q_type in ('选择题', '判断题', '多选题'):
            if q_type == '选择题' or q_type == '多选题':
                ua = ''.join(sorted(list(user_ans)))
                sa = ''.join(sorted(list(std_ans)))
            else:
                ua = user_ans
                sa = std_ans
            return 1 if (ua != '' and ua == sa) else 0

        if q_type == '填空题':
            """填空题判分：支持多空 + 每空多答案

            约定：
            - 标准答案格式：不同空用 ";;" 分隔；每空多答案用 ";" 分隔
              例如：北京;北平;;上海;沪
            - 用户提交：
              - 单空：直接提交字符串
              - 多空：前端提交 JSON 数组字符串，如 "[\"a\",\"b\"]"
            """
            if not user_ans:
                return 0

            # 解析用户答案：可能是 JSON 数组字符串，也可能是普通字符串
            ua_list = None
            try:
                tmp = json.loads(user_ans)
                if isinstance(tmp, list):
                    ua_list = [str(x).strip() for x in tmp]
            except Exception:
                ua_list = None

            # 解析标准答案：
            # - 不同空之间用 ";;" 分隔
            # - 同一空的多个可接受答案用 ";" 分隔
            # 例：北京;北平;;上海;沪
            std = (std_ans or '').strip()
            std_blanks = [s.strip() for s in std.split(';;')] if std else ['']

            # 单空：候选集用 ";" 分隔
            def match_one(user_one, std_one):
                user_one = (user_one or '').strip()
                if not user_one:
                    return False
                cand = [c.strip() for c in (std_one or '').split(';') if c and c.strip()]
                if not cand:
                    cand = [(std_one or '').strip()]
                return any(user_one == c for c in cand)

            # 多空：逐空匹配，空数需一致；多余答案/缺失答案均算错
            if ua_list is not None:
                if len(ua_list) != len(std_blanks):
                    return 0
                return 1 if all(match_one(ua_list[i], std_blanks[i]) for i in range(len(std_blanks))) else 0

            # 非 JSON：按"第一空"处理（兼容历史单输入实现）
            if len(std_blanks) > 1:
                return 1 if match_one(user_ans, std_blanks[0]) else 0
            return 1 if match_one(user_ans, std_blanks[0]) else 0

        # 其它题型（简答等）：当前策略为"只要有作答就算对"
        return 1 if user_ans != '' else 0

    @staticmethod
    def submit(exam_id, user_id, answers):
        """提交考试：写入每题作答与 is_correct，并更新 exams.total_score/status"""
        exam_row = db.session.execute(
            text('SELECT * FROM exams WHERE id=:exam_id'), {'exam_id': exam_id}
        ).fetchone()
        if not exam_row:
            return None
        exam = dict(exam_row._mapping)
        if exam['user_id'] != user_id or exam['status'] == 'submitted':
            return None

        cfg = ExamLegacyService._parse_config_json(exam.get('config_json'))
        source = ExamLegacyService._normalize_source(cfg.get('source'))

        # 检查考试是否超时（宽限 60 秒）
        started_at_raw = exam.get('started_at') or exam.get('created_at')
        duration_min = int(cfg.get('duration') or exam.get('duration_minutes') or 0)
        if started_at_raw and duration_min > 0:
            from datetime import timedelta
            if isinstance(started_at_raw, str):
                try:
                    started_at_raw = datetime.fromisoformat(started_at_raw)
                except (ValueError, TypeError):
                    started_at_raw = None
            if started_at_raw:
                deadline = started_at_raw + timedelta(minutes=duration_min, seconds=60)
                if datetime.utcnow() > deadline:
                    return {'error': 'exam_expired', 'message': '考试已超时，无法提交'}

        ans_map = {}
        for a in (answers or []):
            try:
                qid = int(a.get('question_id'))
            except Exception:
                continue
            ans_map[qid] = (a.get('user_answer') or '').strip()

        from app.core.utils.portable_question_format import portable_question_to_internal

        if source == 'user_bank':
            rows = db.session.execute(
                text("""
                SELECT eq.id as eq_id, eq.question_id, eq.score_val,
                       q.type, q.content, q.options, q.answer, q.analysis, q.tags, q.difficulty
                FROM exam_questions eq
                JOIN user_bank_questions q ON q.id = eq.question_id
                WHERE eq.exam_id=:exam_id
                """),
                {'exam_id': exam_id},
            ).fetchall()
            scope = "user_bank"
        else:
            rows = db.session.execute(
                text("""
                SELECT eq.id as eq_id, eq.question_id, eq.score_val,
                       q.type, q.content, q.options, q.answer, q.analysis, q.tags, q.difficulty
                FROM exam_questions eq
                JOIN questions q ON q.id = eq.question_id
                WHERE eq.exam_id=:exam_id
                """),
                {'exam_id': exam_id},
            ).fetchall()
            scope = "question_center"

        total = len(rows)
        correct = 0
        total_score = 0.0
        pending_count = 0
        grading_mode = (cfg.get('grading_mode') or 'auto_full').strip().lower()
        if grading_mode not in ('auto_full', 'ai', 'manual'):
            grading_mode = 'auto_full'

        for r in rows:
            rm = r._mapping
            qid = rm['question_id']
            user_ans = ans_map.get(qid, '')
            portable = {
                "id": qid,
                "type": rm["type"] or "",
                "content": rm["content"] or "",
                "options": safe_json_load(rm["options"], []),
                "answer": safe_json_load(rm["answer"], []),
                "analysis": rm["analysis"] or "",
                "tags": safe_json_load(rm["tags"], []),
                "difficulty": rm["difficulty"] if rm["difficulty"] is not None else 1,
            }
            internal, _errors = portable_question_to_internal(portable, scope=scope)

            q_type_val = internal.get("q_type") or ""
            is_essay = q_type_val not in ('选择题', '判断题', '多选题', '填空题')

            if is_essay and grading_mode == 'manual':
                is_correct = None  # 待人工评分
            elif is_essay and grading_mode == 'ai':
                from app.modules.exam.services.ai_grading_service import grade_essay_answer
                ai_result = grade_essay_answer(
                    question_content=internal.get("content") or "",
                    standard_answer=internal.get("answer") or "",
                    user_answer=user_ans,
                )
                is_correct = ai_result if ai_result is not None else (1 if user_ans != '' else 0)
            else:
                is_correct = ExamLegacyService._grade_answer(q_type_val, user_ans, internal.get("answer"))

            db.session.execute(
                text('UPDATE exam_questions SET user_answer=:user_answer, is_correct=:is_correct, answered_at=CURRENT_TIMESTAMP WHERE id=:eq_id'),
                {'user_answer': user_ans, 'is_correct': is_correct, 'eq_id': rm['eq_id']}
            )

            if is_correct is None:
                pending_count += 1
            elif is_correct:
                correct += 1
                total_score += float(rm['score_val'] or 0)

        status = 'pending_review' if pending_count > 0 else 'submitted'
        db.session.execute(
            text("UPDATE exams SET total_score=:total_score, status=:status, submitted_at=CURRENT_TIMESTAMP WHERE id=:exam_id"),
            {'total_score': total_score, 'status': status, 'exam_id': exam_id}
        )
        db.session.commit()

        return {
            'total': total,
            'correct': correct,
            'total_score': total_score,
            'pending_count': pending_count,
            'status': status,
        }


# 向后兼容别名
Exam = ExamLegacyService
