# -*- coding: utf-8 -*-
"""后台校园管理聚合服务。"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.core.extensions import db
from app.core.utils.credential_crypto import decrypt_secret
from app.models.edu_schedule import EduGradeSnapshot, EduScheduleCredential, EduScheduleSnapshot
from app.models.user import User


_KIND_TO_MODEL = {
    "schedule": EduScheduleSnapshot,
    "grades": EduGradeSnapshot,
}


def _format_time(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError:
            return str(value)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed.replace(microsecond=0).isoformat() + "Z"


def _safe_json_loads(value: str) -> Dict[str, Any]:
    try:
        data = json.loads(value or "{}")
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _decrypt_or_error(value: str) -> str:
    try:
        return decrypt_secret(value)
    except Exception:
        return "解密失败"


def _contains_any(item: Dict[str, Any], search: str, fields: Iterable[str]) -> bool:
    needle = (search or "").strip().lower()
    if not needle:
        return True
    return any(needle in str(item.get(field) or "").lower() for field in fields)


def _paginate(items: List[Dict[str, Any]], page: int, size: int) -> Tuple[List[Dict[str, Any]], int]:
    total = len(items)
    start = max(0, (page - 1) * size)
    end = start + size
    return items[start:end], total


def _schedule_course_count(payload: Dict[str, Any]) -> int:
    courses = payload.get("courses") if isinstance(payload.get("courses"), list) else []
    practice = payload.get("practice_courses") if isinstance(payload.get("practice_courses"), list) else []
    return len(courses) + len(practice)


def _grade_course_count(payload: Dict[str, Any]) -> int:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    raw_count = summary.get("course_count")
    if isinstance(raw_count, int):
        return raw_count
    grades = payload.get("grades") if isinstance(payload.get("grades"), list) else []
    return len(grades)


def _snapshot_course_count(kind: str, payload: Dict[str, Any]) -> int:
    if kind == "grades":
        return _grade_course_count(payload)
    return _schedule_course_count(payload)


def _student_info(payload: Dict[str, Any]) -> Dict[str, str]:
    student = payload.get("student") if isinstance(payload.get("student"), dict) else {}
    return {
        "name": str(student.get("name") or ""),
        "student_no": str(student.get("student_no") or ""),
        "class_name": str(student.get("class_name") or ""),
        "major_name": str(student.get("major_name") or ""),
        "college_name": str(student.get("college_name") or ""),
    }


def _grade_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    return {
        "course_count": summary.get("course_count") or _grade_course_count(payload),
        "total_credits": summary.get("total_credits") or 0,
        "gpa": summary.get("gpa") or 0,
        "total_grade_points": summary.get("total_grade_points") or 0,
    }


def _flatten_schedule_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    courses = payload.get("courses") if isinstance(payload.get("courses"), list) else []
    for course in courses:
        if not isinstance(course, dict):
            continue
        rows.append(
            {
                "type": "course",
                "weekday": str(course.get("day") or ""),
                "section": str(course.get("section") or ""),
                "course_name": str(course.get("course_name") or ""),
                "teacher": str(course.get("teacher") or ""),
                "location": str(course.get("location") or ""),
                "weeks": str(course.get("weeks") or ""),
                "credits": str(course.get("credits") or ""),
                "assessment": str(course.get("assessment") or ""),
            }
        )

    practice_courses = payload.get("practice_courses") if isinstance(payload.get("practice_courses"), list) else []
    for course in practice_courses:
        if not isinstance(course, dict):
            continue
        rows.append(
            {
                "type": "practice",
                "weekday": "实践",
                "section": str(course.get("section") or ""),
                "course_name": str(course.get("course_name") or ""),
                "teacher": str(course.get("teacher") or ""),
                "location": str(course.get("location") or course.get("campus") or ""),
                "weeks": str(course.get("weeks") or ""),
                "credits": str(course.get("credits") or ""),
                "assessment": str(course.get("assessment") or ""),
            }
        )
    return rows


def _flatten_grade_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    grades = payload.get("grades") if isinstance(payload.get("grades"), list) else []
    rows: List[Dict[str, Any]] = []
    for grade in grades:
        if not isinstance(grade, dict):
            continue
        rows.append(
            {
                "course_code": str(grade.get("course_code") or ""),
                "course_name": str(grade.get("course_name") or ""),
                "course_type": str(grade.get("course_type") or ""),
                "teacher": str(grade.get("teacher") or ""),
                "credits": str(grade.get("credits") or ""),
                "score": str(grade.get("score") or ""),
                "grade_point": str(grade.get("grade_point") or ""),
                "assessment": str(grade.get("assessment") or ""),
                "exam_type": str(grade.get("exam_type") or ""),
            }
        )
    return rows


def _snapshot_base(row: Any, user: User, kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    term = payload.get("term") if isinstance(payload.get("term"), dict) else {}
    data = {
        "id": int(row.id),
        "kind": kind,
        "user_id": int(user.id),
        "username": user.username,
        "xnm": str(row.xnm or term.get("xnm") or ""),
        "xqm": str(row.xqm or term.get("xqm") or ""),
        "term_label": str(row.term_label or term.get("label") or ""),
        "student": _student_info(payload),
        "course_count": _snapshot_course_count(kind, payload),
        "fetched_at": _format_time(row.fetched_at),
    }
    if kind == "grades":
        data["summary"] = _grade_summary(payload)
    return data


def _latest_credential(rows: List[EduScheduleCredential]) -> EduScheduleCredential:
    return max(
        rows,
        key=lambda row: (
            _format_time(row.updated_at) or "",
            _format_time(row.created_at) or "",
            int(row.id or 0),
        ),
    )


def _credential_display(credential: EduScheduleCredential) -> Dict[str, str]:
    return {
        "jwxt_username": _decrypt_or_error(credential.jwxt_username_ciphertext),
        "jwxt_password": _decrypt_or_error(credential.jwxt_password_ciphertext),
    }


def _credential_group_key(credential: EduScheduleCredential) -> Tuple[str, str, str]:
    display = _credential_display(credential)
    username = display["jwxt_username"]
    password = display["jwxt_password"]
    if username == "解密失败" or password == "解密失败":
        return ("credential", str(credential.id), "")
    return ("secret", username, password)


def _record_key(username: str, password: str) -> str:
    return hashlib.sha256(f"{username}\0{password}".encode("utf-8")).hexdigest()


def _snapshot_credential_display(row: Any) -> Optional[Dict[str, str]]:
    username_ciphertext = getattr(row, "jwxt_username_ciphertext", None)
    password_ciphertext = getattr(row, "jwxt_password_ciphertext", None)
    if not username_ciphertext or not password_ciphertext:
        return None
    username = _decrypt_or_error(username_ciphertext)
    password = _decrypt_or_error(password_ciphertext)
    if username == "解密失败" or password == "解密失败":
        return None
    return {"jwxt_username": username, "jwxt_password": password}


def _snapshot_item_sort_key(item: Dict[str, Any]) -> Tuple[str, int, int]:
    kind_weight = 1 if item.get("kind") == "grades" else 0
    return (str(item.get("fetched_at") or ""), kind_weight, int(item.get("id") or 0))


def _student_from_snapshot_items(items: List[Dict[str, Any]]) -> Dict[str, str]:
    for item in sorted(items, key=_snapshot_item_sort_key, reverse=True):
        student = item.get("student") if isinstance(item.get("student"), dict) else {}
        if student.get("name"):
            return {
                "name": str(student.get("name") or ""),
                "student_no": str(student.get("student_no") or ""),
                "class_name": str(student.get("class_name") or ""),
                "major_name": str(student.get("major_name") or ""),
                "college_name": str(student.get("college_name") or ""),
            }
    return {
        "name": "未查询",
        "student_no": "",
        "class_name": "",
        "major_name": "",
        "college_name": "",
    }


def _snapshot_term_key(item: Dict[str, Any]) -> Tuple[str, str]:
    return (str(item.get("xnm") or ""), str(item.get("xqm") or ""))


def _snapshot_items(kind: str) -> List[Dict[str, Any]]:
    model = _KIND_TO_MODEL[kind]
    rows = (
        db.session.query(model, User)
        .join(User, User.id == model.user_id)
        .order_by(model.fetched_at.desc(), model.id.desc())
        .all()
    )
    items: List[Dict[str, Any]] = []
    for snapshot, user in rows:
        credentials = _snapshot_credential_display(snapshot)
        if credentials is None:
            continue
        payload = _safe_json_loads(snapshot.payload_json)
        item = _snapshot_base(snapshot, user, kind, payload)
        item.update(credentials)
        item["record_key"] = _record_key(credentials["jwxt_username"], credentials["jwxt_password"])
        items.append(item)
    return items


def _merge_latest_snapshot_terms(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen_terms = set()
    for item in sorted(items, key=_snapshot_item_sort_key, reverse=True):
        term_key = _snapshot_term_key(item)
        if term_key in seen_terms:
            continue
        seen_terms.add(term_key)
        merged.append(item)
    return merged


def _credential_groups(rows: List[EduScheduleCredential]) -> Dict[Tuple[str, str, str], List[EduScheduleCredential]]:
    grouped: Dict[Tuple[str, str, str], List[EduScheduleCredential]] = {}
    for credential in rows:
        grouped.setdefault(_credential_group_key(credential), []).append(credential)
    return grouped


def _detail_url(record_key: str) -> str:
    return f"/admin/campus/records/{record_key}"


def _record_from_snapshot_group(
    *,
    record_key: str,
    jwxt_username: str,
    jwxt_password: str,
    schedule_items: List[Dict[str, Any]],
    grade_items: List[Dict[str, Any]],
    credential_id: int = 0,
    created_at: Optional[Any] = None,
    updated_at: Optional[Any] = None,
) -> Dict[str, Any]:
    all_snapshot_items = schedule_items + grade_items
    student = _student_from_snapshot_items(all_snapshot_items)
    latest_snapshot = max(all_snapshot_items, key=_snapshot_item_sort_key, default=None)
    return {
        "credential_id": int(credential_id or 0),
        "record_key": record_key,
        "jwxt_username": jwxt_username,
        "jwxt_password": jwxt_password,
        "username_hint": "",
        "student_name": student.get("name") or "未查询",
        "student": student,
        "schedule_snapshot_count": len(schedule_items),
        "grade_snapshot_count": len(grade_items),
        "latest_fetched_at": latest_snapshot.get("fetched_at") if latest_snapshot else None,
        "created_at": _format_time(created_at),
        "updated_at": _format_time(updated_at),
        "detail_url": _detail_url(record_key),
    }


def _record_entries_from_credentials(rows: List[EduScheduleCredential]) -> List[Dict[str, Any]]:
    credential_groups = _credential_groups(rows)
    snapshot_groups: Dict[str, Dict[str, Any]] = {}
    for kind in ("schedule", "grades"):
        for item in _snapshot_items(kind):
            key = item["record_key"]
            group = snapshot_groups.setdefault(
                key,
                {
                    "record_key": key,
                    "jwxt_username": item["jwxt_username"],
                    "jwxt_password": item["jwxt_password"],
                    "schedule": [],
                    "grades": [],
                },
            )
            group[kind].append(item)

    entries: List[Dict[str, Any]] = []
    groups_with_snapshots = set()
    for group in snapshot_groups.values():
        credential_group_key = ("secret", group["jwxt_username"], group["jwxt_password"])
        credentials = credential_groups.get(credential_group_key) or []
        credential = _latest_credential(credentials) if credentials else None
        schedule_items = _merge_latest_snapshot_terms(group["schedule"])
        grade_items = _merge_latest_snapshot_terms(group["grades"])
        entries.append(
            {
                "record_key": group["record_key"],
                "record": _record_from_snapshot_group(
                    record_key=group["record_key"],
                    jwxt_username=group["jwxt_username"],
                    jwxt_password=group["jwxt_password"],
                    schedule_items=schedule_items,
                    grade_items=grade_items,
                    credential_id=int(credential.id) if credential else 0,
                    created_at=credential.created_at if credential else None,
                    updated_at=credential.updated_at if credential else None,
                ),
                "schedule_snapshots": schedule_items,
                "grade_snapshots": grade_items,
            }
        )
        groups_with_snapshots.add(credential_group_key)

    for credential_group_key, credentials in credential_groups.items():
        if credential_group_key in groups_with_snapshots:
            continue
        credential = _latest_credential(credentials)
        display = _credential_display(credential)
        key = _record_key(display["jwxt_username"], display["jwxt_password"])
        entries.append(
            {
                "record_key": key,
                "record": _record_from_snapshot_group(
                    record_key=key,
                    jwxt_username=display["jwxt_username"],
                    jwxt_password=display["jwxt_password"],
                    schedule_items=[],
                    grade_items=[],
                    credential_id=int(credential.id),
                    created_at=credential.created_at,
                    updated_at=credential.updated_at,
                ),
                "schedule_snapshots": [],
                "grade_snapshots": [],
            }
        )

    entries.sort(
        key=lambda entry: (
            str(entry["record"].get("latest_fetched_at") or ""),
            int(entry["record"].get("credential_id") or 0),
        ),
        reverse=True,
    )
    return entries


class CampusManagementService:
    """读取后台校园管理所需的凭据与查询快照。"""

    @staticmethod
    def summary() -> Dict[str, int]:
        return {
            "credential_count": int(EduScheduleCredential.query.count()),
            "schedule_snapshot_count": int(EduScheduleSnapshot.query.count()),
            "grade_snapshot_count": int(EduGradeSnapshot.query.count()),
        }

    @staticmethod
    def list_credentials(search: str = "", page: int = 1, size: int = 20) -> Dict[str, Any]:
        rows = (
            db.session.query(EduScheduleCredential, User)
            .join(User, User.id == EduScheduleCredential.user_id)
            .order_by(EduScheduleCredential.updated_at.desc(), EduScheduleCredential.id.desc())
            .all()
        )
        items: List[Dict[str, Any]] = []
        for credential, user in rows:
            item = {
                "id": int(credential.id),
                "user_id": int(user.id),
                "username": user.username,
                "jwxt_username": _decrypt_or_error(credential.jwxt_username_ciphertext),
                "jwxt_password": _decrypt_or_error(credential.jwxt_password_ciphertext),
                "username_hint": credential.username_hint or "",
                "created_at": _format_time(credential.created_at),
                "updated_at": _format_time(credential.updated_at),
            }
            if _contains_any(item, search, ("user_id", "username", "jwxt_username", "username_hint")):
                items.append(item)

        page_items, total = _paginate(items, page, size)
        return {
            "items": page_items,
            "total": total,
            "page": page,
            "size": size,
            "summary": CampusManagementService.summary(),
        }

    @staticmethod
    def list_records(search: str = "", page: int = 1, size: int = 20) -> Dict[str, Any]:
        rows = (
            EduScheduleCredential.query
            .order_by(EduScheduleCredential.updated_at.desc(), EduScheduleCredential.id.desc())
            .all()
        )
        items: List[Dict[str, Any]] = []
        for entry in _record_entries_from_credentials(rows):
            item = entry["record"]
            if _contains_any(
                item,
                search,
                ("jwxt_username", "jwxt_password", "username_hint", "student_name"),
            ):
                items.append(item)
        page_items, total = _paginate(items, page, size)
        return {
            "items": page_items,
            "total": total,
            "page": page,
            "size": size,
            "summary": CampusManagementService.summary(),
        }

    @staticmethod
    def list_snapshots(
        kind: str,
        *,
        user_id: Optional[int] = None,
        search: str = "",
        page: int = 1,
        size: int = 20,
    ) -> Dict[str, Any]:
        model = _KIND_TO_MODEL[kind]
        query = db.session.query(model, User).join(User, User.id == model.user_id)
        if user_id:
            query = query.filter(model.user_id == int(user_id))
        query = query.order_by(model.fetched_at.desc(), model.id.desc())

        items: List[Dict[str, Any]] = []
        for snapshot, user in query.all():
            payload = _safe_json_loads(snapshot.payload_json)
            item = _snapshot_base(snapshot, user, kind, payload)
            if _contains_any(item, search, ("user_id", "username", "xnm", "xqm", "term_label")):
                items.append(item)

        page_items, total = _paginate(items, page, size)
        return {
            "items": page_items,
            "total": total,
            "page": page,
            "size": size,
            "summary": CampusManagementService.summary(),
        }

    @staticmethod
    def get_record_detail(record_key: str) -> Optional[Dict[str, Any]]:
        rows = EduScheduleCredential.query.order_by(EduScheduleCredential.updated_at.desc()).all()
        selected_entry = next(
            (entry for entry in _record_entries_from_credentials(rows) if entry["record_key"] == str(record_key)),
            None,
        )
        if selected_entry is None:
            return None
        return {
            "record": selected_entry["record"],
            "schedule_snapshots": selected_entry["schedule_snapshots"],
            "grade_snapshots": selected_entry["grade_snapshots"],
            "summary": CampusManagementService.summary(),
        }

    @staticmethod
    def get_snapshot_detail(kind: str, snapshot_id: int) -> Optional[Dict[str, Any]]:
        model = _KIND_TO_MODEL[kind]
        row = (
            db.session.query(model, User)
            .join(User, User.id == model.user_id)
            .filter(model.id == int(snapshot_id))
            .first()
        )
        if row is None:
            return None

        snapshot, user = row
        payload = _safe_json_loads(snapshot.payload_json)
        base = _snapshot_base(snapshot, user, kind, payload)
        base["payload"] = payload
        base["items"] = _flatten_grade_items(payload) if kind == "grades" else _flatten_schedule_items(payload)
        return base
