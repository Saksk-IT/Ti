# -*- coding: utf-8 -*-
import base64


_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+XnX8AAAAASUVORK5CYII="
)


def test_upload_route_allows_forum_image_burst_requests(app, auth_client, monkeypatch, tmp_path):
    """论坛页会并发拉取多张头像/封面，上传文件直链不能被默认 10/s 限流误伤。"""
    forum_dir = tmp_path / "forum"
    forum_dir.mkdir(parents=True, exist_ok=True)
    (forum_dir / "burst-test.png").write_bytes(_PNG_BYTES)

    monkeypatch.setitem(app.config, "UPLOAD_FOLDER", str(tmp_path))

    statuses = [
        auth_client.get("/uploads/forum/burst-test.png").status_code
        for _ in range(12)
    ]

    assert statuses == [200] * 12
