# -*- coding: utf-8 -*-
"""
题目模型
"""
from app.core.extensions import db
from app.core.utils.json_helpers import safe_json_load
from sqlalchemy import text


class Question:
    """题目模型"""

    @staticmethod
    def _row_to_internal(row, *, scope: str):
        """把 DB(PQF) 行转换为旧页面/接口可用的字段（q_type/answer/explanation/填空 __ 等）。"""
        from app.core.utils.portable_question_format import portable_question_to_internal

        r = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
        portable = {
            "id": r.get("id"),
            "type": r.get("type") or "",
            "content": r.get("content") or "",
            "options": safe_json_load(r.get("options"), []),
            "answer": safe_json_load(r.get("answer"), []),
            "analysis": r.get("analysis") or "",
            "tags": safe_json_load(r.get("tags"), []),
            "difficulty": r.get("difficulty") if r.get("difficulty") is not None else 1,
        }
        internal, _errors = portable_question_to_internal(portable, scope=scope)
        # 兼容旧字段命名
        r["portable_type"] = portable.get("type") or ""
        r["portable_content"] = portable.get("content") or ""
        r["portable_options"] = portable.get("options") or []
        r["portable_answer"] = portable.get("answer") if portable.get("answer") is not None else []
        r["portable_tags"] = portable.get("tags") or []
        r["q_type"] = internal.get("q_type") or ""
        r["content"] = internal.get("content") or ""
        r["options"] = internal.get("options") or []
        r["answer"] = internal.get("answer") or ""
        r["explanation"] = internal.get("explanation") or ""
        r["difficulty"] = internal.get("difficulty") if internal.get("difficulty") is not None else (portable.get("difficulty") or 1)
        return r
    
    @staticmethod
    def get_by_id(question_id):
        """通过ID获取题目"""
        row = db.session.execute(
            text('SELECT * FROM questions WHERE id = :qid'), {'qid': question_id}
        ).fetchone()
        if row:
            return Question._row_to_internal(row, scope="question_center")
        return None
    
    @staticmethod
    def get_list_legacy(subject='all', q_type='all', mode='quiz', user_id=None):
        """获取题目列表（旧版，全表扫描 + Python 层过滤，保留兼容）

        .. deprecated::
            使用 :meth:`get_list` 替代，该方法将在下个版本删除。
        """
        import warnings
        warnings.warn(
            "get_list_legacy() 已废弃，请使用 get_list() 替代",
            DeprecationWarning,
            stacklevel=2,
        )
        from app.core.utils.subject_permissions import get_user_restricted_subjects
        from app.core.utils.portable_question_format import q_type_to_portable_type

        uid = user_id or -1

        restricted_subject_ids = set(get_user_restricted_subjects(int(user_id))) if user_id else set()

        sql = """
            SELECT q.*, s.name as subject,
                   CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
                   CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN favorites f ON q.id = f.question_id AND f.user_id = :uid
            LEFT JOIN mistakes m ON q.id = m.question_id AND m.user_id = :uid
            WHERE 1=1
        """
        params = {'uid': uid}

        if subject != 'all':
            sql += " AND s.name = :subject"
            params['subject'] = subject

        if q_type != 'all':
            portable_type = q_type_to_portable_type(q_type)
            sql += " AND q.type = :qtype"
            params['qtype'] = portable_type

        if mode == 'favorites':
            sql += " AND f.id IS NOT NULL"
        elif mode == 'mistakes':
            sql += " AND m.id IS NOT NULL"

        sql += " ORDER BY q.id"

        rows = db.session.execute(text(sql), params).fetchall()

        questions = []
        for row in rows:
            q = Question._row_to_internal(row, scope="question_center")
            sid = q.get('subject_id')
            if sid and sid in restricted_subject_ids:
                continue
            questions.append(q)

        return questions

    @staticmethod
    def get_list(
        subject='all',
        q_type='all',
        mode='quiz',
        user_id=None,
        page: int = 1,
        per_page: int = 20,
        tag_ids: list | None = None,
        accessible_subject_ids: list | None = None,
    ) -> tuple[list, int]:
        """获取题目列表（SQL 层分页 + 权限/标签下推）

        Returns:
            (questions, total) 元组
        """
        from app.core.utils.portable_question_format import q_type_to_portable_type

        uid = user_id or -1

        base_from = """
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN favorites f ON q.id = f.question_id AND f.user_id = :uid
            LEFT JOIN mistakes m ON q.id = m.question_id AND m.user_id = :uid
            WHERE 1=1
        """
        params: dict = {'uid': uid}

        # 科目筛选
        if subject != 'all':
            base_from += " AND s.name = :subject"
            params['subject'] = subject

        # 题型筛选
        if q_type != 'all':
            portable_type = q_type_to_portable_type(q_type)
            base_from += " AND q.type = :qtype"
            params['qtype'] = portable_type

        # 模式筛选
        if mode == 'favorites':
            base_from += " AND f.id IS NOT NULL"
        elif mode == 'mistakes':
            base_from += " AND m.id IS NOT NULL"

        # 权限过滤下推 SQL
        if accessible_subject_ids is not None:
            if not accessible_subject_ids:
                return [], 0
            ph = ','.join(f':_asid_{i}' for i in range(len(accessible_subject_ids)))
            base_from += f" AND q.subject_id IN ({ph})"
            for i, sid in enumerate(accessible_subject_ids):
                params[f'_asid_{i}'] = sid

        # 标签筛选下推 SQL
        if tag_ids is not None:
            if not tag_ids:
                return [], 0
            ph = ','.join(f':_tid_{i}' for i in range(len(tag_ids)))
            base_from += f" AND q.id IN ({ph})"
            for i, tid in enumerate(tag_ids):
                params[f'_tid_{i}'] = tid

        # COUNT 查询
        count_sql = "SELECT COUNT(1) " + base_from
        total = db.session.execute(text(count_sql), params).scalar() or 0

        if total == 0:
            return [], 0

        # 分页
        if page < 1:
            page = 1
        offset = (page - 1) * per_page

        select_sql = (
            "SELECT q.*, s.name as subject,"
            " CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,"
            " CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake "
            + base_from
            + " ORDER BY q.id LIMIT :_limit OFFSET :_offset"
        )
        params['_limit'] = per_page
        params['_offset'] = offset

        rows = db.session.execute(text(select_sql), params).fetchall()

        questions = []
        for row in rows:
            q = Question._row_to_internal(row, scope="question_center")
            questions.append(q)

        return questions, total
    
    @staticmethod
    def get_count(subject='all', q_type='all', mode='quiz', user_id=None):
        """获取题目数量（添加权限过滤）"""
        from app.core.utils.subject_permissions import get_user_accessible_subjects
        from app.core.utils.portable_question_format import q_type_to_portable_type

        uid = user_id or -1

        # 获取用户可访问的科目ID
        if user_id:
            accessible_subject_ids = get_user_accessible_subjects(user_id)
            if not accessible_subject_ids:
                return 0
        else:
            accessible_subject_ids = None

        if mode == 'favorites':
            base_sql = """FROM questions q
                      LEFT JOIN subjects s ON q.subject_id = s.id
                      JOIN favorites f ON f.question_id = q.id AND f.user_id = :uid
                      WHERE 1=1"""
            params = {'uid': uid}
        elif mode == 'mistakes':
            base_sql = """FROM questions q
                      LEFT JOIN subjects s ON q.subject_id = s.id
                      JOIN mistakes m ON m.question_id = q.id AND m.user_id = :uid
                      WHERE 1=1"""
            params = {'uid': uid}
        else:
            base_sql = "FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id WHERE 1=1"
            params = {}

        if subject != 'all':
            base_sql += " AND s.name = :subject"
            params['subject'] = subject

        if q_type != 'all':
            base_sql += " AND q.type = :qtype"
            params['qtype'] = q_type_to_portable_type(q_type)

        # 权限过滤：只统计可访问科目的题目
        if accessible_subject_ids is not None:
            placeholders = ','.join([f':sid_{i}' for i in range(len(accessible_subject_ids))])
            base_sql += f" AND q.subject_id IN ({placeholders})"
            for i, sid in enumerate(accessible_subject_ids):
                params[f'sid_{i}'] = sid

        sql = "SELECT COUNT(1) " + base_sql
        return db.session.execute(text(sql), params).scalar()
    
    @staticmethod
    def get_subjects(user_id=None):
        """获取所有科目（添加权限过滤）"""
        from app.core.utils.subject_permissions import get_user_accessible_subjects

        if user_id:
            # 返回用户可访问的科目
            accessible_subject_ids = get_user_accessible_subjects(user_id)
            if not accessible_subject_ids:
                return []

            placeholders = ','.join([f':sid_{i}' for i in range(len(accessible_subject_ids))])
            params = {f'sid_{i}': sid for i, sid in enumerate(accessible_subject_ids)}
            rows = db.session.execute(
                text(f'SELECT name FROM subjects WHERE id IN ({placeholders})'),
                params
            ).fetchall()
        else:
            # 未登录用户：返回空列表
            rows = []

        return [row._mapping['name'] for row in rows]
    
    @staticmethod
    def get_types():
        """获取所有题型"""
        from app.core.utils.portable_question_format import portable_type_to_q_type

        rows = db.session.execute(text('SELECT DISTINCT type FROM questions')).fetchall()
        out = []
        for r in rows or []:
            t = (r._mapping['type'] if r else "") or ""
            if not t:
                continue
            # 题库中心：essay 默认展示为"简答题"
            out.append(portable_type_to_q_type(t))
        # 去重排序，保持稳定
        return sorted(list(set(out)))
