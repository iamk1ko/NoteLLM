from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.dependencies import (get_current_user, get_redis, get_minio, get_rabbitmq_channel)
from app.schemas.file_storage import (
    FileListResponse,
    FileStorageOut,
    FileChunkUploadIn,
)
from app.schemas.response import ApiResponse
from app.services import FileStorageService
from app.crud import FileStorageCRUD
from app.models import User, FileStorage
from aio_pika.abc import AbstractChannel
from minio import Minio
from redis.asyncio import Redis

router = APIRouter(tags=["files"])


@router.post("/files/upload/chunk", response_model=ApiResponse[dict])
async def upload_chunk(
        file_md5: str = Form(..., description="文件MD5"),
        chunk_index: int = Form(..., description="分片索引，从0开始"),
        total_chunks: int = Form(..., description="总分片数"),
        chunk_size: int = Form(..., description="当前分片大小（字节）"),
        total_size: int = Form(..., description="文件总大小（字节）"),
        file_name: str = Form(..., description="文件名称"),
        content_type: str = Form(..., description="文件MIME类型"),
        is_public: bool = Form(False, description="是否为公共文件"),
        file_chunk: UploadFile = File(..., description="分片文件本体"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        redis_client: Redis = Depends(get_redis),
        minio_client: Minio = Depends(get_minio),
        rabbit_channel: AbstractChannel = Depends(get_rabbitmq_channel),
) -> ApiResponse[dict]:
    """分片上传接口（预留逻辑）。"""

    payload = FileChunkUploadIn(
        file_md5=file_md5,
        chunk_index=chunk_index,
        total_chunks=total_chunks,
        chunk_size=chunk_size,
        file_size=total_size,
        file_name=file_name,
        content_type=content_type,
        is_public=is_public,
    )
    result = await FileStorageService(
        db,
        redis_client=redis_client,
        minio_client=minio_client,
        rabbitmq_channel=rabbit_channel,
    ).upload_chunk(current_user, payload, file_chunk)
    return ApiResponse.ok(result)


@router.get("/files/upload/is_complete/{file_id}", response_model=ApiResponse[FileStorageOut])
async def upload_is_complete(
        file_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        redis_client: Redis = Depends(get_redis),
        minio_client: Minio = Depends(get_minio),
        rabbit_channel: AbstractChannel = Depends(get_rabbitmq_channel),
) -> ApiResponse[FileStorageOut]:
    """TODO: 检查完整文件是否已经完成上传并合并。即数据库中文件状态为 `FileStorageStatus.UPLOADED.value` (目前仅是初步设计，还需完善)。
    """

    file_obj = await FileStorageService(
        db,
        redis_client=redis_client,
        minio_client=minio_client,
        rabbitmq_channel=rabbit_channel,
    ).upload_is_complete(current_user, file_id)
    return ApiResponse.ok(FileStorageOut.model_validate(file_obj))


@router.get("/files", response_model=ApiResponse[FileListResponse])
def list_files(
        page: int = Query(1, ge=1, description="页码，从 1 开始"),
        size: int = Query(10, ge=1, le=100, description="每页数量"),
        include_public: bool = Query(True, description="是否包含公共文件"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
) -> ApiResponse[FileListResponse]:
    """查询知识库文件列表（分页）。"""

    items, total = FileStorageCRUD.get_user_files(
        db, current_user.id, page=page, size=size, include_public=include_public
    )
    payload = FileListResponse(
        items=[FileStorageOut.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )
    return ApiResponse.ok(payload)


@router.get("/files/{file_id}", response_model=ApiResponse[FileStorageOut])
def get_file_detail(
        file_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
) -> ApiResponse[FileStorageOut]:
    """获取文件详情。"""

    file_obj: FileStorage = FileStorageCRUD.get_user_file(db, file_id, current_user.id)
    if not file_obj:
        raise HTTPException(status_code=404, detail="文件不存在或无权限")
    return ApiResponse.ok(FileStorageOut.model_validate(file_obj))


@router.get("/files/public", response_model=ApiResponse[FileListResponse])
def list_public_files(
        page: int = Query(1, ge=1, description="页码，从 1 开始"),
        size: int = Query(10, ge=1, le=100, description="每页数量"),
        db: Session = Depends(get_db),
) -> ApiResponse[FileListResponse]:
    """查询公共文件列表（分页）。"""

    items, total = FileStorageCRUD.get_public_files(db, page=page, size=size)
    payload = FileListResponse(
        items=[FileStorageOut.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )
    return ApiResponse.ok(payload)


@router.delete("/files/{file_id}", response_model=ApiResponse[dict])
def delete_file(
        file_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
) -> ApiResponse[dict]:
    """删除文件（硬删除）。"""

    file_obj = FileStorageCRUD.get_file_by_id(db, file_id)
    if not file_obj:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 权限控制：普通用户只能删除自己的文件
    if current_user.role != "admin" and file_obj.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除该文件")

    ok = FileStorageCRUD.delete_file(db, file_id)
    if not ok:
        raise HTTPException(status_code=400, detail="删除失败")

    return ApiResponse.ok({"success": True})
