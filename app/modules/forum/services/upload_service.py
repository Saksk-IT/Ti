# -*- coding: utf-8 -*-
"""论坛图片上传服务"""
import json
import os
import posixpath
from typing import Optional

from flask import current_app
from sqlalchemy import inspect, text

from app.core.extensions import db
from app.models.forum import ForumUpload

_TRACKING_TABLE_NAME = ForumUpload.__tablename__
_MISSING_TABLE_WARNING_KEY = 'forum_upload_tracking_missing_table_warned'


def _read_json_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    return []


def _extract_forum_filenames(image_urls) -> list[str]:
    filenames: list[str] = []
    for url in image_urls or []:
        normalized = str(url or '').strip()
        if normalized.startswith('/uploads/forum/'):
            filename = _normalize_forum_filename(normalized.replace('/uploads/forum/', '', 1).strip())
            if filename:
                filenames.append(filename)
    return list(dict.fromkeys(filenames))


def _normalize_forum_filename(value: str) -> str | None:
    normalized = str(value or '').strip().replace('\\', '/')
    if not normalized:
        return None
    if '/' in normalized:
        return None
    if normalized != posixpath.basename(normalized):
        return None
    if normalized in {'.', '..'}:
        return None
    return normalized


def _normalize_forum_relative_path(value: str) -> str | None:
    normalized = str(value or '').strip().replace('\\', '/')
    if not normalized:
        return None
    compact = posixpath.normpath(normalized).lstrip('/')
    if not compact.startswith('forum/'):
        return None
    suffix = compact[len('forum/'):]
    if not _normalize_forum_filename(suffix):
        return None
    return f'forum/{suffix}'


def _delete_files_by_relative_path(relative_paths: list[str]) -> list[str]:
    upload_folder = current_app.config['UPLOAD_FOLDER']
    deleted_files: list[str] = []
    normalized_paths = []
    for relative_path in relative_paths:
        safe_path = _normalize_forum_relative_path(relative_path)
        if safe_path:
            normalized_paths.append(safe_path)
    for filepath in dict.fromkeys(normalized_paths):
        full_path = os.path.join(upload_folder, filepath)
        if not os.path.exists(full_path):
            continue
        try:
            os.remove(full_path)
            deleted_files.append(filepath)
        except Exception as exc:
            current_app.logger.error(f"删除图片失败 {filepath}: {exc}")
    return deleted_files


def _delete_files_by_filename(filenames: list[str]) -> list[str]:
    return _delete_files_by_relative_path([f'forum/{filename}' for filename in filenames])


def _warn_tracking_table_missing(operation: str) -> None:
    warned = current_app.extensions.setdefault(_MISSING_TABLE_WARNING_KEY, False)
    if warned:
        return
    current_app.extensions[_MISSING_TABLE_WARNING_KEY] = True
    current_app.logger.warning(
        'forum_uploads 表不存在，论坛上传追踪已降级（operation=%s）；建议尽快执行数据库迁移。',
        operation,
    )


def _has_tracking_table(operation: str) -> bool:
    try:
        exists = inspect(db.engine).has_table(_TRACKING_TABLE_NAME)
    except Exception as exc:
        current_app.logger.error(f'检查论坛上传追踪表失败: {exc}', exc_info=True)
        return False
    if not exists:
        _warn_tracking_table_missing(operation)
    return exists


def _get_post_image_filenames(post_id: int) -> list[str]:
    row = db.session.execute(text("""
        SELECT cover_image, images
        FROM forum_posts
        WHERE id = :post_id
    """), {'post_id': post_id}).fetchone()
    if not row:
        return []

    cover_image = row._mapping.get('cover_image')
    image_urls = []
    if cover_image:
        image_urls.append(str(cover_image))
    image_urls.extend(_read_json_list(row._mapping.get('images')))
    return _extract_forum_filenames(image_urls)


def track_upload(filename: str, filepath: str, uploader_id: int) -> int:
    """
    追踪上传的图片

    Args:
        filename: 文件名
        filepath: 文件路径（相对于UPLOAD_FOLDER）
        uploader_id: 上传者ID

    Returns:
        upload_id: 上传记录ID
    """
    if not _has_tracking_table('track_upload'):
        return 0

    record = ForumUpload(
        filename=filename,
        filepath=filepath,
        uploader_id=uploader_id,
        is_attached=False,
    )
    db.session.add(record)
    db.session.commit()
    return int(record.id or 0)


def attach_uploads_to_post(post_id: int, image_urls: list[str]) -> None:
    """
    将上传的图片关联到帖子

    Args:
        post_id: 帖子ID
        image_urls: 图片URL列表（如 ['/uploads/forum/xxx.jpg']）
    """
    if not image_urls:
        return

    if not _has_tracking_table('attach_uploads_to_post'):
        return

    filenames = _extract_forum_filenames(image_urls)

    if not filenames:
        return

    # 批量更新
    placeholders = ','.join([f':fn{i}' for i in range(len(filenames))])
    params = {'post_id': post_id}
    for i, fn in enumerate(filenames):
        params[f'fn{i}'] = fn

    db.session.execute(text(f"""
        UPDATE forum_uploads
        SET post_id = :post_id, is_attached = true
        WHERE filename IN ({placeholders}) AND is_attached = false
    """), params)
    db.session.commit()


def detach_uploads_from_post(post_id: int) -> None:
    """
    将帖子的图片标记为未关联（用于删除帖子时）

    Args:
        post_id: 帖子ID
    """
    if not _has_tracking_table('detach_uploads_from_post'):
        return

    db.session.execute(text("""
        UPDATE forum_uploads
        SET is_attached = false, post_id = NULL
        WHERE post_id = :post_id
    """), {'post_id': post_id})
    db.session.commit()


def cleanup_orphan_uploads(hours: int = 24) -> tuple[int, list[str]]:
    """
    清理孤儿上传文件（上传后超过指定时间仍未关联到帖子）

    Args:
        hours: 超过多少小时未关联视为孤儿

    Returns:
        (deleted_count, deleted_files): 删除的记录数和文件列表
    """
    if not _has_tracking_table('cleanup_orphan_uploads'):
        return 0, []

    dialect = db.engine.dialect.name

    # PostgreSQL 和 SQLite 的时间计算语法不同
    if dialect == 'postgresql':
        time_condition = "uploaded_at < NOW() - (:hours * INTERVAL '1 hour')"
        params = {'hours': int(hours)}
    else:
        # SQLite
        time_condition = "uploaded_at < datetime('now', '-' || :hours || ' hours')"
        params = {'hours': int(hours)}

    try:
        # 查询孤儿文件
        rows = db.session.execute(text(f"""
            SELECT id, filename, filepath
            FROM forum_uploads
            WHERE is_attached = false
            AND {time_condition}
        """), params).fetchall()

        if not rows:
            db.session.rollback()
            return 0, []

        deleted_files = []
        deleted_ids = []

        for row in rows:
            upload_id = row[0]
            filepath = row[2]

            safe_path = _normalize_forum_relative_path(filepath)
            if safe_path:
                deleted_files.extend(_delete_files_by_relative_path([safe_path]))

            deleted_ids.append(upload_id)

        # 删除数据库记录
        if deleted_ids:
            placeholders = ','.join([f':id{i}' for i in range(len(deleted_ids))])
            delete_params = {f'id{i}': uid for i, uid in enumerate(deleted_ids)}
            db.session.execute(text(f"""
                DELETE FROM forum_uploads WHERE id IN ({placeholders})
            """), delete_params)
            db.session.commit()
        else:
            db.session.rollback()

        return len(deleted_ids), deleted_files
    except Exception:
        db.session.rollback()
        raise


def cleanup_post_images(post_id: int, old_cover: Optional[str], old_images: list[str],
                        new_cover: Optional[str], new_images: list[str]) -> list[str]:
    """
    清理帖子编辑后不再使用的图片

    Args:
        post_id: 帖子ID
        old_cover: 旧封面图URL
        old_images: 旧图片列表
        new_cover: 新封面图URL
        new_images: 新图片列表

    Returns:
        deleted_files: 删除的文件路径列表
    """
    # 收集旧图片
    old_urls = set()
    if old_cover:
        old_urls.add(old_cover)
    old_urls.update(old_images or [])

    # 收集新图片
    new_urls = set()
    if new_cover:
        new_urls.add(new_cover)
    new_urls.update(new_images or [])

    # 找出不再使用的图片
    removed_urls = old_urls - new_urls
    if not removed_urls:
        return []

    removed_filenames = _extract_forum_filenames(removed_urls)

    if not removed_filenames:
        return []

    deleted_files = _delete_files_by_filename(removed_filenames)

    if not _has_tracking_table('cleanup_post_images'):
        return deleted_files

    for filename in removed_filenames:
        try:
            db.session.execute(text("""
                DELETE FROM forum_uploads
                WHERE filename = :filename AND post_id = :post_id
            """), {'filename': filename, 'post_id': post_id})
        except Exception as exc:
            current_app.logger.error(f"删除上传记录失败 {filename}: {exc}")

    db.session.commit()
    return deleted_files


def delete_post_images(post_id: int) -> list[str]:
    """
    删除帖子的所有关联图片（物理文件+数据库记录）

    Args:
        post_id: 帖子ID

    Returns:
        deleted_files: 删除的文件路径列表
    """
    if not _has_tracking_table('delete_post_images'):
        return _delete_files_by_filename(_get_post_image_filenames(post_id))

    rows = db.session.execute(text("""
        SELECT filename, filepath FROM forum_uploads WHERE post_id = :post_id
    """), {'post_id': post_id}).fetchall()

    if not rows:
        return []

    deleted_files = _delete_files_by_relative_path([row[1] for row in rows])

    db.session.execute(text("""
        DELETE FROM forum_uploads WHERE post_id = :post_id
    """), {'post_id': post_id})
    db.session.commit()

    return deleted_files
