"""
Адаптеры для облачных хранилищ.

Абстрактный класс CloudClient позволяет пайплайну не зависеть
от конкретного хранилища (Nextcloud, S3, локальная папка).

Студент: реализуйте методы download(), list_files(), upload()
в классе NextcloudClient или S3Client.
"""
from __future__ import annotations

import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class CloudClient(ABC):
    """Абстрактный адаптер облачного хранилища."""

    @abstractmethod
    def download(self, remote_path: str, local_path: str) -> str:
        """
        Скачивает файл из хранилища.

        Args:
            remote_path: Путь в хранилище, например "/videos/lecture.mp4"
            local_path:  Локальный путь для сохранения файла.

        Returns:
            Абсолютный путь к скачанному файлу.
        """

    @abstractmethod
    def list_files(self, remote_dir: str, extension: str | None = None) -> list[str]:
        """
        Возвращает список файлов в директории хранилища.

        Args:
            remote_dir: Директория в хранилище.
            extension:  Фильтр по расширению, например ".mp4".
        """

    @abstractmethod
    def upload(self, local_path: str, remote_path: str) -> bool:
        """
        Загружает файл в хранилище.

        Returns:
            True если успешно.
        """

    def download_if_needed(self, remote_path: str, local_path: str) -> str:
        """Скачивает файл только если он ещё не скачан."""
        local = Path(local_path)
        if local.exists():
            return str(local)
        return self.download(remote_path, local_path)


class NextcloudClient(CloudClient):
    """
    Клиент для Nextcloud через WebDAV.

    Требует установки: pip install webdavclient3

    Переменные окружения:
        NEXTCLOUD_HOST      — https://your-nextcloud.example.com
        NEXTCLOUD_USERNAME  — логин
        NEXTCLOUD_PASSWORD  — пароль или app token
        NEXTCLOUD_ROOT      — корневой путь WebDAV (обычно /remote.php/dav/files/USER/)
    """

    def __init__(
        self,
        host: str | None = None,
        username: str | None = None,
        password: str | None = None,
        root_path: str | None = None,
    ):
        self.host = host or os.environ["NEXTCLOUD_HOST"]
        self.username = username or os.environ["NEXTCLOUD_USERNAME"]
        self.password = password or os.environ["NEXTCLOUD_PASSWORD"]
        self.root_path = root_path or os.getenv("NEXTCLOUD_ROOT", "/remote.php/dav/files/")
        self._client = None

    def _get_client(self):
        """Ленивая инициализация WebDAV клиента."""
        if self._client is None:
            try:
                import webdav3.client as wc
            except ImportError:
                raise ImportError(
                    "Установите webdavclient3: pip install webdavclient3"
                )
            options = {
                "webdav_hostname": self.host,
                "webdav_login": self.username,
                "webdav_password": self.password,
                "webdav_root": self.root_path + self.username + "/",
            }
            self._client = wc.Client(options)
        return self._client

    def download(self, remote_path: str, local_path: str) -> str:
        """
        Скачивает файл из Nextcloud.

        TODO: Реализуйте этот метод.
        Подсказка: self._get_client().download_sync(remote_path, local_path)
        """
        client = self._get_client()
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        # --- Ваш код здесь ---
        try:
            client.download_sync(remote_path=remote_path, local_path=local_path)
            return Path(local_path).absolute()
        except Exception as e:
            print(f'Ошибка в NextcloudClient.download: {e}')
        # raise NotImplementedError(
        #     "Реализуйте метод download() в NextcloudClient. "
        #     "См. задание docs/tasks/01_cloud_fetch.md"
        # )

    def list_files(self, remote_dir: str, extension: str | None = None) -> list[str]:
        """
        TODO: Реализуйте метод.
        Подсказка: self._get_client().list(remote_dir)
        """
        raise NotImplementedError("Реализуйте list_files()")

    def upload(self, local_path: str, remote_path: str) -> bool:
        """
        TODO: Реализуйте метод.
        Подсказка: self._get_client().upload_sync(remote_path, local_path)
        """
        raise NotImplementedError("Реализуйте upload()")


class S3Client(CloudClient):
    """
    Клиент для Amazon S3 и совместимых хранилищ (MinIO, Yandex.Cloud).

    Требует установки: pip install boto3

    Переменные окружения:
        AWS_ACCESS_KEY_ID
        AWS_SECRET_ACCESS_KEY
        AWS_DEFAULT_REGION
        S3_BUCKET_NAME
        S3_ENDPOINT_URL  — для MinIO/Yandex: https://storage.yandexcloud.net
    """

    def __init__(
        self,
        bucket: str | None = None,
        endpoint_url: str | None = None,
    ):
        self.bucket = bucket or os.environ["S3_BUCKET_NAME"]
        self.endpoint_url = endpoint_url or os.getenv("S3_ENDPOINT_URL")
        self._s3 = None

    def _get_s3(self):
        if self._s3 is None:
            try:
                import boto3
            except ImportError:
                raise ImportError("Установите boto3: pip install boto3")
            self._s3 = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
            )
        return self._s3

    def download(self, remote_path: str, local_path: str) -> str:
        """
        TODO: Реализуйте скачивание из S3.
        Подсказка: self._get_s3().download_file(self.bucket, remote_path, local_path)
        """
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        # --- Ваш код здесь ---
        raise NotImplementedError(
            "Реализуйте метод download() в S3Client. "
            "Документация: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-examples.html"
        )

    def list_files(self, remote_dir: str, extension: str | None = None) -> list[str]:
        """TODO: реализуйте через paginator для обхода > 1000 объектов."""
        raise NotImplementedError("Реализуйте list_files()")

    def upload(self, local_path: str, remote_path: str) -> bool:
        """TODO: реализуйте загрузку в S3."""
        raise NotImplementedError("Реализуйте upload()")


class LocalClient(CloudClient):
    """
    Псевдо-клиент для локальных файлов.
    Используется для тестирования без облака.
    """

    def __init__(self, base_dir: str = "data/raw_videos"):
        self.base_dir = Path(base_dir)

    def download(self, remote_path: str, local_path: str) -> str:
        src = self.base_dir / Path(remote_path).name
        if str(src) != local_path:
            shutil.copy2(src, local_path)
        return str(local_path)

    def list_files(self, remote_dir: str, extension: str | None = None) -> list[str]:
        p = self.base_dir / remote_dir
        files = list(p.iterdir()) if p.exists() else []
        if extension:
            files = [f for f in files if f.suffix == extension]
        return [str(f) for f in files]

    def upload(self, local_path: str, remote_path: str) -> bool:
        dst = self.base_dir / remote_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, dst)
        return True


def get_cloud_client(cloud_type: str, **kwargs) -> CloudClient:
    """Фабричная функция: возвращает нужный клиент по строковому имени."""
    clients = {
        "nextcloud": NextcloudClient,
        "s3": S3Client,
        "local": LocalClient,
    }
    if cloud_type not in clients:
        raise ValueError(f"Неизвестный тип хранилища: '{cloud_type}'. "
                         f"Доступные: {list(clients.keys())}")
    return clients[cloud_type](**kwargs)
