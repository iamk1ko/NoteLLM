from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass

from minio import Minio


@dataclass
class FileReadResult:
    file_path: str
    file_size: int
    is_streamed: bool


class MinioFileReader:
    def __init__(self, minio_client: Minio, memory_threshold_mb: int):
        self.minio = minio_client
        self.memory_threshold_bytes = max(1, memory_threshold_mb) * 1024 * 1024  # 至少1MB

    def download(self, bucket_name: str, object_name: str) -> FileReadResult:
        stat = self.minio.stat_object(bucket_name, object_name)
        object_size = 0 if stat.size is None else stat.size
        is_small = object_size <= self.memory_threshold_bytes
        obj = self.minio.get_object(bucket_name, object_name)
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            total_size = 0
            if is_small:
                data = obj.read()
                total_size = len(data)
                temp_file.write(data)
            else:
                for data in obj.stream(32 * 1024):  # 32KB块读取
                    total_size += len(data)
                    temp_file.write(data)
            temp_file.flush()
            temp_file.close()
            return FileReadResult(
                file_path=temp_file.name,
                file_size=total_size,
                is_streamed=not is_small,
            )
        finally:
            obj.close()
            obj.release_conn()

    @staticmethod
    def cleanup(file_path: str) -> None:
        try:
            os.remove(file_path)
        except Exception:
            pass
