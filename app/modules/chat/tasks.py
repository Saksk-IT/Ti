# -*- coding: utf-8 -*-
"""音频转码任务（可被 RQ 异步调用，也可同步调用）"""
import json
import logging
import os
import shutil
import subprocess

logger = logging.getLogger(__name__)


def _ffmpeg_exists() -> bool:
    try:
        return shutil.which('ffmpeg') is not None
    except Exception:
        return False


def _transcode(src_abs: str, dst_abs: str, codec_args: list[str]) -> tuple[bool, str]:
    if not _ffmpeg_exists():
        return False, 'ffmpeg_not_found'
    cmd = ['ffmpeg', '-y', '-i', src_abs, '-vn'] + codec_args + [dst_abs]
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if p.returncode != 0:
            return False, (p.stderr.decode('utf-8', errors='ignore')[:4000] or 'ffmpeg_failed')
        return True, ''
    except Exception as e:
        return False, str(e)


def transcode_audio_task(
    message_id: int,
    raw_abs: str,
    chat_dir: str,
    base: str,
    duration: float,
    raw_url: str,
) -> None:
    """转码音频并更新消息 content（RQ 任务入口）

    先尝试 m4a(AAC)，失败回退 mp3，都失败则保留 raw。
    """
    from app.core.extensions import db
    from sqlalchemy import text

    m4a_abs = os.path.join(chat_dir, f"{base}.m4a")
    m4a_url = f"/uploads/chat/{base}.m4a"
    mp3_abs = os.path.join(chat_dir, f"{base}.mp3")
    mp3_url = f"/uploads/chat/{base}.mp3"

    m4a_ok, m4a_err = _transcode(
        raw_abs, m4a_abs,
        ['-c:a', 'aac', '-b:a', '64k', '-ar', '44100', '-ac', '1', '-movflags', '+faststart'],
    )

    mp3_ok = False
    if not m4a_ok:
        _cleanup(m4a_abs)
        mp3_ok, mp3_err = _transcode(
            raw_abs, mp3_abs,
            ['-c:a', 'libmp3lame', '-b:a', '96k', '-ar', '44100', '-ac', '1'],
        )
        if not mp3_ok:
            _cleanup(mp3_abs)
            logger.warning(
                "audio transcode all failed: msg=%s raw=%s m4a_err=%s mp3_err=%s",
                message_id, raw_abs, m4a_err, mp3_err,
            )
            return  # 保留 raw，不更新消息

    best_url = m4a_url if m4a_ok else mp3_url
    content_obj = {
        'url': best_url,
        'url_raw': raw_url,
        'url_m4a': m4a_url if m4a_ok else None,
        'url_mp3': mp3_url if mp3_ok else None,
        'duration': duration if duration > 0 else None,
    }
    content_str = json.dumps(content_obj, ensure_ascii=False)

    try:
        db.session.execute(text(
            'UPDATE chat_messages SET content = :c WHERE id = :mid'
        ), {'c': content_str, 'mid': message_id})
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error("audio transcode update msg failed: msg=%s err=%s", message_id, e)


def _cleanup(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
