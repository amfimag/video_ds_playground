"""
Этап 1: Загрузка видео из облачного хранилища.
"""
from __future__ import annotations

import re
from pathlib import Path

from src.core.base import Stage
from src.core.cloud_client import get_cloud_client
from src.core.registry import register_stage


@register_stage("fetch")
class FetchStage(Stage):
    """
    Скачивает видеофайл из облачного хранилища в локальную директорию.

    Читает из data:
        video_path (str): URI видео. Форматы:
            - nextcloud:///videos/lecture.mp4
            - s3:///bucket-name/videos/lecture.mp4
            - local:///abs/path/to/file.mp4
            - /abs/path/to/file.mp4  (уже локальный файл)

    Добавляет в data:
        video_path (str): обновлённый локальный путь после скачивания
        fetch_meta (dict): {source, filename, size_mb}
    """

    def __init__(
        self,
        cloud: str = "local",
        remote_path: str | None = None,
        local_dir: str = "data/raw_videos",
        **cloud_kwargs,
    ):
        self.cloud = cloud
        self.remote_path = remote_path
        self.local_dir = Path(local_dir)
        self.cloud_kwargs = cloud_kwargs

    def run(self, data: dict, context: dict) -> dict:
        video_uri = self.remote_path or data.get("video_path", "")

        # Если уже локальный путь — ничего не делаем
        if Path(video_uri).exists():
            data["video_path"] = str(video_uri)
            data["fetch_meta"] = {"source": "local", "filename": Path(video_uri).name}
            return data
     
        # Разбираем URI: nextcloud:///path/to/file.mp4
        cloud_type, remote = self._parse_uri(video_uri)
        filename = Path(remote).name
        local_path = str(self.local_dir / filename)
        self.local_dir.mkdir(parents=True, exist_ok=True)

        client = get_cloud_client(cloud_type or self.cloud, **self.cloud_kwargs)
        local_path = client.download_if_needed(remote, local_path)

        size_mb = Path(local_path).stat().st_size / 1024 / 1024
        context.get("logger").info(f"    Скачано: {filename} ({size_mb:.1f} МБ)")

        data["video_path"] = local_path
        data["fetch_meta"] = {
            "source": cloud_type or self.cloud,
            "filename": filename,
            "size_mb": round(size_mb, 2),
        }
        return data

    @staticmethod
    def _parse_uri(uri: str) -> tuple[str | None, str]:
        """Разбирает URI вида 'nextcloud:///path' → ('nextcloud', '/path')"""
        m = re.match(r"^(\w+):///(.*)", uri)
        if m:
            return m.group(1), "/" + m.group(2)
        return None, uri

    def get_config_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "cloud": {"type": "string", "enum": ["nextcloud", "s3", "local"]},
                "remote_path": {"type": "string"},
                "local_dir": {"type": "string"},
            },
        }
