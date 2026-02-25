# -*- coding: utf-8 -*-
from app.core.extensions import db
from sqlalchemy import text


def _get_accessible_subject_rows(conn=None, uid=None):
    """获取用户可访问的科目（id/name），并过滤锁定科目。

    conn 参数保留用于向后兼容（未迁移的调用方仍可传入），
    但内部统一使用 db.session。
    """
    if uid:
        from app.core.utils.subject_permissions import get_user_accessible_subjects

        accessible_subject_ids = get_user_accessible_subjects(uid)
        if not accessible_subject_ids:
            return []
        placeholders = ",".join([f":id_{i}" for i in range(len(accessible_subject_ids))])
        params = {f"id_{i}": sid for i, sid in enumerate(accessible_subject_ids)}
        rows = db.session.execute(
            text(
                f"SELECT id, name FROM subjects WHERE id IN ({placeholders}) AND (is_locked=false OR is_locked IS NULL) ORDER BY id"
            ),
            params,
        ).fetchall()
        return [dict(r._mapping) for r in rows]

    rows = db.session.execute(
        text("SELECT id, name FROM subjects WHERE (is_locked=false OR is_locked IS NULL) ORDER BY id")
    ).fetchall()
    return [dict(r._mapping) for r in rows]
