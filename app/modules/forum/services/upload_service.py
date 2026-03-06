# -*- coding: utf-8 -*-
"""论坛图片上传服务"""
import os
from typing import Optional
from flask import current_app
from sqlalchemy import text
from app.core.extensions import db
from app.models.forum import ForumUpload


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
    result = db.session.execute(text("""
        INSERT INTO forum_uploads (filename, filepath, uploader_id, is_attached, uploaded_at)
        VALUES (:filename, :filepath, :uploader_id, false, NOW())
        RETURNING id
    """), {
        'filename': filename,
        'filepath': filepath,
        'uploader_id': uploader_id,
    })
    upload_id = result.fetchone()[0]
    db.session.commit()
    return upload_id


def attach_uploads_to_post(post_id: int, image_urls: list[str]) -> None:
    """
    将上传的图片关联到帖子

    Args:
        post_id: 帖子ID
        image_urls: 图片URL列表（如 ['/uploads/forum/xxx.jpg']）
    """
    if not image_urls:
        return

    # 提取文件名
    filenames = []
    for url in image_urls:
        if url.startswith('/uploads/forum/'):
            filename = url.replace('/uploads/forum/', '')
            filenames.append(filename)

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
    dialect = db.engine.dialect.name

    # PostgreSQL 和 SQLite 的时间计算语法不同
    if dialect == 'postgresql':
        time_condition = "uploaded_at < NOW() - INTERVAL ':hours HOUR'"
        params = {'hours': hours}
    else:
        # SQLite
        time_condition = "uploaded_at < datetime('now', '-' || :hours || ' hours')"
        params = {'hours': hours}

    # 查询孤儿文件
    rows = db.session.execute(text(f"""
        SELECT id, filename, filepath
        FROM forum_uploads
        WHERE is_attached = false
        AND {time_condition}
    """), params).fetchall()

    if not rows:
        return 0, []

    upload_folder = current_app.config['UPLOAD_FOLDER']
    deleted_files = []
    deleted_ids = []

    for row in rows:
        upload_id = row[0]
        filename = row[1]
        filepath = row[2]

        # 删除物理文件
        full_path = os.path.join(upload_folder, filepath)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                deleted_files.append(filepath)
            except Exception as e:
                current_app.logger.error(f"删除孤儿文件失败 {filepath}: {e}")
                continue

        deleted_ids.append(upload_id)

    # 删除数据库记录
    if deleted_ids:
        placeholders = ','.join([f':id{i}' for i in range(len(deleted_ids))])
        params = {f'id{i}': uid for i, uid in enumerate(deleted_ids)}
        db.session.execute(text(f"""
            DELETE FROM forum_uploads WHERE id IN ({placeholders})
        """), params)
        db.session.commit()

    return len(deleted_ids), deleted_files


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

    # 提取文件名
    removed_filenames = []
    for url in removed_urls:
        if url.startswith('/uploads/forum/'):
            filename = url.replace('/uploads/forum/', '')
            removed_filenames.append(filename)

    if not removed_filenames:
        return []

    upload_folder = current_app.config['UPLOAD_FOLDER']
    deleted_files = []

    for filename in removed_filenames:
        filepath = f'forum/{filename}'
        full_path = os.path.join(upload_folder, filepath)

        # 删除物理文件
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                deleted_files.append(filepath)
            except Exception as e:
                current_app.logger.error(f"删除图片失败 {filepath}: {e}")
                continue

        # 删除数据库记录
        try:
            db.session.execute(text("""
                DELETE FROM forum_uploads
                WHERE filename = :filename AND post_id = :post_id
            """), {'filename': filename, 'post_id': post_id})
        except Exception as e:
            current_app.logger.error(f"删除上传记录失败 {filename}: {e}")

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
    # 查询帖子的所有图片
    rows = db.session.execute(text("""
        SELECT filename, filepath FROM forum_uploads WHERE post_id = :post_id
    """), {'post_id': post_id}).fetchall()

    if not rows:
        return []

    upload_folder = current_app.config['UPLOAD_FOLDER']
    deleted_files = []

    for row in rows:
        filename = row[0]
        filepath = row[1]
        full_path = os.path.join(upload_folder, filepath)

        # 删除物理文件
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                deleted_files.append(filepath)
            except Exception as e:
                current_app.logger.error(f"删除帖子图片失败 {filepath}: {e}")

    # 删除数据库记录（CASCADE会自动删除）
    db.session.execute(text("""
        DELETE FROM forum_uploads WHERE post_id = :post_id
    """), {'post_id': post_id})
    db.session.commit()

    return deleted_files
