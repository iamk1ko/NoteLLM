from __future__ import annotations

import hashlib
from typing import Any
from datetime import timedelta

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    File,
    Form,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_db
from app.dependencies import (
    get_current_user,
    get_redis,
    get_minio,
    get_rabbitmq_channel,
    get_milvus,
)
from app.schemas.file_storage import (
    FileListResponse,
    FileStorageOut,
    FileChunkUploadIn,
)
from pydantic import BaseModel, Field
from app.core.logging import get_logger
from app.services.file_cleanup_service import FileCleanupService
from app.schemas.response import ApiResponse
from app.services import FileStorageService, MilvusVectorStore
from app.crud import FileStorageCRUD
from app.models import User, FileStorageStatus
from app.services.vectorization.vector_store import MilvusVectorStore
from aio_pika.abc import AbstractChannel
from minio import Minio
from redis.asyncio import Redis

router = APIRouter(tags=["files"])
logger = get_logger(__name__)


class FileExistsResponse(BaseModel):
    """文件存在性检查响应模型。"""

    exists: bool = Field(..., description="是否存在")
    file_id: int | None = Field(None, description="已存在文件ID")
    filename: str | None = Field(None, description="已存在文件名")
    status: int | None = Field(None, description="文件状态")
    upload_time: str | None = Field(None, description="上传时间")


@router.post("/files", response_model=ApiResponse[dict])
async def upload_file_simple(
        file: UploadFile = File(..., description="上传文件"),
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
        redis_client: Redis = Depends(get_redis),
        minio_client: Minio = Depends(get_minio),
        rabbit_channel: AbstractChannel = Depends(get_rabbitmq_channel),
) -> ApiResponse[FileStorageOut | dict[str, Any]]:
    """简单单文件上传接口（适配前端直接上传）。

    说明：
    - 重复文件（用户内）返回 exists=true，并携带已存在文件信息
    - status=FAILED 允许重新上传
    """

    # 1. 计算文件 MD5
    file_md5_hash = hashlib.md5()
    file_content = await file.read()
    file_md5_hash.update(file_content)
    file_md5 = file_md5_hash.hexdigest()

    # 重复上传检查（用户内去重）
    existing = await FileStorageCRUD.get_user_file_by_md5_async(
        db, current_user.id, file_md5
    )
    if existing and existing.status != FileStorageStatus.FAILED.value:
        logger.info(
            "文件已存在，阻止上传：user_id={}, file_id={}, file_md5={}, status={}",
            current_user.id,
            existing.id,
            file_md5,
            existing.status,
        )
        return ApiResponse.ok(
            {
                "exists": True,
                "file_id": existing.id,
                "filename": existing.filename,
                "status": existing.status,
                "upload_time": existing.upload_time.isoformat()
                if existing.upload_time
                else None,
            }
        )

    # 2. 获取文件大小和名称
    file_size = len(file_content)
    file_name = file.filename or "unknown"
    content_type = file.content_type or "application/octet-stream"

    # 3. 重置文件指针供 upload_chunk 使用
    await file.seek(0)

    # 4. 构造分片 payload (单分片模式: 0/1)
    payload = FileChunkUploadIn(
        file_md5=file_md5,
        chunk_index=0,
        total_chunks=1,
        chunk_size=file_size,
        file_size=file_size,
        file_name=file_name,
        content_type=content_type,
        is_public=False,  # 默认为私有
    )

    # 5. 调用分片上传逻辑
    # 注意: upload_chunk 内部会处理 FileStorage 的创建/更新
    await FileStorageService(
        db,
        redis_client=redis_client,
        minio_client=minio_client,
        rabbitmq_channel=rabbit_channel,
    ).upload_chunk(current_user, payload, file)

    logger.info(
        "文件上传请求完成：user_id={}, file_md5={}, file_name={}",
        current_user.id,
        file_md5,
        file_name,
    )

    # 6. 获取并返回文件记录
    # 因为 upload_chunk 已经创建了记录，我们可以查回来
    # 注意: object_name 在 upload_chunk 中生成规则是 f"{file_md5}/{file_name}"
    object_name = f"{file_md5}/{file_name}"
    file_obj = await FileStorageCRUD.get_file_by_object_name_async(
        db, current_user.id, object_name
    )

    if not file_obj:
        raise HTTPException(status_code=500, detail="文件上传后未找到记录")

    return ApiResponse.ok(
        {
            "exists": False,
            "file": FileStorageOut.model_validate(file_obj),
        }
    )


@router.get("/files/check", response_model=ApiResponse[FileExistsResponse])
async def check_file_exists(
        file_md5: str = Query(..., description="文件MD5"),
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
) -> ApiResponse[FileExistsResponse]:
    """检查文件是否已存在（用户内去重）。"""

    file_obj = await FileStorageCRUD.get_user_file_by_md5_async(
        db, current_user.id, file_md5
    )
    if file_obj and file_obj.status != FileStorageStatus.FAILED.value:
        logger.info(
            "文件已存在检查命中：user_id={}, file_id={}, file_md5={}, status={}",
            current_user.id,
            file_obj.id,
            file_md5,
            file_obj.status,
        )
        payload = FileExistsResponse(
            exists=True,
            file_id=file_obj.id,
            filename=file_obj.filename,
            status=file_obj.status,
            upload_time=file_obj.upload_time.isoformat()
            if file_obj.upload_time
            else None,
        )
        return ApiResponse.ok(payload)

    logger.info(
        "文件不存在或允许重传：user_id={}, file_md5={}",
        current_user.id,
        file_md5,
    )
    return ApiResponse.ok(
        FileExistsResponse(
            exists=False, file_id=None, filename=None, status=None, upload_time=None
        )
    )


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
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
        redis_client: Redis = Depends(get_redis),
        minio_client: Minio = Depends(get_minio),
        rabbit_channel: AbstractChannel = Depends(get_rabbitmq_channel),
) -> ApiResponse[dict]:
    """分片上传接口。

    说明：
    - 重复文件（用户内）返回 exists=true，并携带已存在文件信息
    - status=FAILED 允许重新上传
    """

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
    # 重复上传检查（用户内去重）
    existing = await FileStorageCRUD.get_user_file_by_md5_async(
        db, current_user.id, file_md5
    )
    if existing and existing.status != FileStorageStatus.FAILED.value:
        if existing.status == FileStorageStatus.UPLOADING.value:
            logger.info(
                "检测到正在上传的同文件，继续分片上传：user_id={}, file_id={}, file_md5={}",
                current_user.id,
                existing.id,
                file_md5,
            )
        else:
            logger.info(
                "文件已存在，阻止分片上传：user_id={}, file_id={}, file_md5={}, status={}",
                current_user.id,
                existing.id,
                file_md5,
                existing.status,
            )
            return ApiResponse.ok(
                {
                    "exists": True,
                    "file_id": existing.id,
                    "status": existing.status,
                }
            )
    logger.info(
        "分片上传请求：user_id={}, file_md5={}, chunk_index={}, total_chunks={}",
        current_user.id,
        file_md5,
        chunk_index,
        total_chunks,
    )
    result = await FileStorageService(
        db,
        redis_client=redis_client,
        minio_client=minio_client,
        rabbitmq_channel=rabbit_channel,
    ).upload_chunk(current_user, payload, file_chunk)
    return ApiResponse.ok(result)


@router.get(
    "/files/upload/is_complete/{file_id}", response_model=ApiResponse[FileStorageOut]
)
async def upload_is_complete(
        file_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
        redis_client: Redis = Depends(get_redis),
        minio_client: Minio = Depends(get_minio),
        rabbit_channel: AbstractChannel = Depends(get_rabbitmq_channel),
) -> ApiResponse[FileStorageOut]:
    """TODO: 检查完整文件是否已经完成上传并合并。即数据库中文件状态为 `FileStorageStatus.UPLOADED.value` (目前仅是初步设计，还需完善)。"""

    logger.debug("查询上传完成状态：file_id={}, user_id={}", file_id, current_user.id)
    file_obj = await FileStorageService(
        db,
        redis_client=redis_client,
        minio_client=minio_client,
        rabbitmq_channel=rabbit_channel,
    ).upload_is_complete(current_user, file_id)
    # Note: upload_is_complete currently returns status (int), not object.
    # But schema expects FileStorageOut.
    # Wait, FileStorageService.upload_is_complete returns int.
    # The original code:
    # file_obj = await FileStorageService(...).upload_is_complete(current_user, file_id)
    # return ApiResponse.ok(FileStorageOut.model_validate(file_obj))
    # This seems BUGGY in original code too if it returns int.
    # Let's check FileStorageService.upload_is_complete implementation.
    # It returns `file_obj.status`.
    # So `FileStorageOut.model_validate(int)` will fail.
    # I should fix this in FileStorageService or here.
    # I'll fix it here by fetching the object.

    file_obj_db = await FileStorageCRUD.get_user_file_async(
        db, file_id, current_user.id
    )
    if not file_obj_db:
        raise HTTPException(status_code=404, detail="文件不存在")

    return ApiResponse.ok(FileStorageOut.model_validate(file_obj_db))


@router.get("/files", response_model=ApiResponse[FileListResponse])
async def list_files(
        page: int = Query(1, ge=1, description="页码，从 1 开始"),
        size: int = Query(10, ge=1, le=100, description="每页数量"),
        include_public: bool = Query(True, description="是否包含公共文件"),
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
) -> ApiResponse[FileListResponse]:
    """查询知识库文件列表（分页）。"""

    items, total = await FileStorageCRUD.get_user_files_async(
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
async def get_file_detail(
        file_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
) -> ApiResponse[FileStorageOut]:
    """获取文件详情。"""

    file_obj = await FileStorageCRUD.get_user_file_async(db, file_id, current_user.id)
    if not file_obj:
        raise HTTPException(status_code=404, detail="文件不存在或无权限")

    return ApiResponse.ok(FileStorageOut.model_validate(file_obj))


@router.get("/files/{file_id}/preview", response_model=ApiResponse[dict])
async def get_file_preview(
        file_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
        minio_client: Minio = Depends(get_minio),
) -> ApiResponse[dict]:
    """获取文件预览地址（MinIO Presigned URL）。"""

    file_obj = await FileStorageCRUD.get_file_by_id_async(db, file_id)
    if not file_obj:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 权限检查：私有文件仅所有者可预览，公共文件所有人可预览
    if not file_obj.is_public and file_obj.user_id != current_user.id:
        # 这里为了安全，也可以直接返回 404
        raise HTTPException(status_code=403, detail="无权预览该文件")

    try:
        # 生成预签名 URL，有效期 1 小时
        url = minio_client.presigned_get_object(
            file_obj.bucket_name,
            file_obj.object_name,
            expires=timedelta(hours=1),
            response_headers={"response-content-disposition": "inline"},
        )
    except Exception as e:
        logger.error(
            "生成预览链接失败：file_id={}, error={}",
            file_id,
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="生成预览链接失败")

    return ApiResponse.ok({"url": url})


@router.get("/files/public", response_model=ApiResponse[FileListResponse])
async def list_public_files(
        page: int = Query(1, ge=1, description="页码，从 1 开始"),
        size: int = Query(10, ge=1, le=100, description="每页数量"),
        db: AsyncSession = Depends(get_async_db),
) -> ApiResponse[FileListResponse]:
    """查询公共文件列表（分页）。"""

    items, total = await FileStorageCRUD.get_public_files_async(
        db, page=page, size=size
    )
    payload = FileListResponse(
        items=[FileStorageOut.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )
    return ApiResponse.ok(payload)


@router.delete("/files/{file_id}", response_model=ApiResponse[dict])
async def delete_file(
        file_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
        milvus: MilvusVectorStore = Depends(get_milvus),
) -> ApiResponse[dict]:
    """删除文件（硬删除：MinIO/Redis/Milvus/MySQL）。"""

    file_obj = await FileStorageCRUD.get_file_by_id_async(db, file_id)
    if not file_obj:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 权限控制：普通用户只能删除自己的文件
    if current_user.role != "admin" and file_obj.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除该文件")

    try:
        cleanup_service = FileCleanupService(db=db, milvus=milvus)
        await cleanup_service.execute_cleanup_direct(
            file_id=file_obj.id,
            user_id=file_obj.user_id,
            file_md5=file_obj.etag or "",
            bucket_name=file_obj.bucket_name,
            object_name=file_obj.object_name,
        )
    except Exception as e:
        logger.error(
            "文件硬删除失败：file_id={}, error={}",
            file_id,
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="文件删除失败")

    logger.info(
        "文件已硬删除：file_id={}, user_id={}, object_name={}",
        file_id,
        current_user.id,
        file_obj.object_name,
    )
    return ApiResponse.ok({"success": True})
