# -*- coding: utf-8 -*-
"""
题目模型
"""
import json
from ..utils.database import get_db


class Question:
    """题目模型"""

    @staticmethod
    def _safe_json_load(raw, default):
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

    @staticmethod
    def _row_to_internal(row, *, scope: str):
        """把 DB(PQF) 行转换为旧页面/接口可用的字段（q_type/answer/explanation/填空 __ 等）。"""
        from app.core.utils.portable_question_format import portable_question_to_internal

        r = dict(row)
        portable = {
            "id": r.get("id"),
            "type": r.get("type") or "",
            "content": r.get("content") or "",
            "options": Question._safe_json_load(r.get("options"), []),
            "answer": Question._safe_json_load(r.get("answer"), []),
            "analysis": r.get("analysis") or "",
            "tags": Question._safe_json_load(r.get("tags"), []),
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
        conn = get_db()
        row = conn.execute(
            'SELECT * FROM questions WHERE id = ?', (question_id,)
        ).fetchone()
        if row:
            return Question._row_to_internal(row, scope="question_center")
        return None
    
    @staticmethod
    def get_list(subject='all', q_type='all', mode='quiz', user_id=None):
        """获取题目列表（添加权限过滤）"""
        from app.core.utils.subject_permissions import get_user_restricted_subjects
        from app.core.utils.portable_question_format import q_type_to_portable_type
        
        conn = get_db()
        uid = user_id or -1

        # 权限过滤（黑名单模式）：一次性取出被限制的 subject_id，避免每题一次 DB 查询（N+1）。
        restricted_subject_ids = set(get_user_restricted_subjects(int(user_id))) if user_id else set()
        
        sql = """
            SELECT q.*, s.name as subject,
                   CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
                   CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN favorites f ON q.id = f.question_id AND f.user_id = ?
            LEFT JOIN mistakes m ON q.id = m.question_id AND m.user_id = ?
            WHERE 1=1
        """
        params = [uid, uid]
        
        # 科目筛选
        if subject != 'all':
            sql += " AND s.name = ?"
            params.append(subject)
        
        # 题型筛选
        if q_type != 'all':
            portable_type = q_type_to_portable_type(q_type)
            sql += " AND q.type = ?"
            params.append(portable_type)
        
        # 模式筛选
        if mode == 'favorites':
            sql += " AND f.id IS NOT NULL"
        elif mode == 'mistakes':
            sql += " AND m.id IS NOT NULL"
        
        sql += " ORDER BY q.id"
        
        rows = conn.execute(sql, params).fetchall()
        
        questions = []
        for row in rows:
            q = Question._row_to_internal(row, scope="question_center")
            
            # 权限检查：如果用户被限制访问该科目，跳过
            sid = q.get('subject_id')
            if sid and sid in restricted_subject_ids:
                continue
            questions.append(q)
        
        return questions
    
    @staticmethod
    def get_count(subject='all', q_type='all', mode='quiz', user_id=None):
        """获取题目数量（添加权限过滤）"""
        from app.core.utils.subject_permissions import get_user_accessible_subjects
        from app.core.utils.portable_question_format import q_type_to_portable_type
        
        conn = get_db()
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
                      JOIN favorites f ON f.question_id = q.id AND f.user_id = ? 
                      WHERE 1=1"""
            params = [uid]
        elif mode == 'mistakes':
            base_sql = """FROM questions q 
                      LEFT JOIN subjects s ON q.subject_id = s.id 
                      JOIN mistakes m ON m.question_id = q.id AND m.user_id = ? 
                      WHERE 1=1"""
            params = [uid]
        else:
            base_sql = "FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id WHERE 1=1"
            params = []
        
        if subject != 'all':
            base_sql += " AND s.name = ?"
            params.append(subject)
        
        if q_type != 'all':
            base_sql += " AND q.type = ?"
            params.append(q_type_to_portable_type(q_type))
        
        # 权限过滤：只统计可访问科目的题目
        if accessible_subject_ids is not None:
            placeholders = ','.join(['?'] * len(accessible_subject_ids))
            base_sql += f" AND q.subject_id IN ({placeholders})"
            params.extend(accessible_subject_ids)
        
        sql = "SELECT COUNT(1) " + base_sql
        return conn.execute(sql, params).fetchone()[0]
    
    @staticmethod
    def get_subjects(user_id=None):
        """获取所有科目（添加权限过滤）"""
        from app.core.utils.subject_permissions import get_user_accessible_subjects
        
        conn = get_db()
        
        if user_id:
            # 返回用户可访问的科目
            accessible_subject_ids = get_user_accessible_subjects(user_id)
            if not accessible_subject_ids:
                return []
            
            placeholders = ','.join(['?'] * len(accessible_subject_ids))
            rows = conn.execute(
                f'SELECT name FROM subjects WHERE id IN ({placeholders})',
                accessible_subject_ids
            ).fetchall()
        else:
            # 未登录用户：返回空列表
            rows = []
        
        return [row[0] for row in rows]
    
    @staticmethod
    def get_types():
        """获取所有题型"""
        from app.core.utils.portable_question_format import portable_type_to_q_type

        conn = get_db()
        rows = conn.execute('SELECT DISTINCT type FROM questions').fetchall()
        out = []
        for r in rows or []:
            t = (r[0] if isinstance(r, (list, tuple)) else (r["type"] if r else "")) or ""
            if not t:
                continue
            # 题库中心：essay 默认展示为“简答题”
            out.append(portable_type_to_q_type(t))
        # 去重排序，保持稳定
        return sorted(list(set(out)))
