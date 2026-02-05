# -*- coding: utf-8 -*-


def _get_accessible_subject_rows(conn, uid):
    """获取用户可访问的科目（id/name），并过滤锁定科目。"""
    if uid:
        from app.core.utils.subject_permissions import get_user_accessible_subjects

        accessible_subject_ids = get_user_accessible_subjects(uid)
        if not accessible_subject_ids:
            return []
        placeholders = ",".join(["?"] * len(accessible_subject_ids))
        rows = conn.execute(
            f"SELECT id, name FROM subjects WHERE id IN ({placeholders}) AND (is_locked=0 OR is_locked IS NULL) ORDER BY id",
            accessible_subject_ids,
        ).fetchall()
        return [dict(r) for r in rows]

    rows = conn.execute(
        "SELECT id, name FROM subjects WHERE (is_locked=0 OR is_locked IS NULL) ORDER BY id"
    ).fetchall()
    return [dict(r) for r in rows]
