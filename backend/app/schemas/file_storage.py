from __future__ import annotations

from datetime import datetime
from typing import Sequence

from pydantic import BaseModel, Field


class FileStorageBase(BaseModel):
    """文件存储基础模型。

    说明：
    - 定义文件的公共字段
    - 不包含 id 和时间戳，用于创建和更新
    """

    filename: str = Field(..., max_length=255, description="原始文件名")
    content_type: str = Field(..., max_length=100, description="文件MIME类型")
    file_size: int = Field(..., ge=0, description="文件大小（字节）")
    is_public: bool = Field(False, description="是否为公共文件：True-公共，False-私有")


class FileUploadCreate(FileStorageBase):
    """文件上传创建模型。

    使用示例：
        ```python
        # 上传私有文件（默认）
        private_file = FileUploadCreate(
            filename="document.pdf",
            content_type="application/pdf",
            file_size=1024000,
            is_public=False
        )

        # 上传公共文件（管理员操作）
        public_file = FileUploadCreate(
            filename="manual.pdf",
            content_type="application/pdf",
            file_size=2048000,
            is_public=True
        )
        ```
    """

    pass


class FileChunkUploadIn(BaseModel):
    """分片上传请求模型。

    说明：
    - 用于分片上传接口的元数据部分
    - file_chunk 本体通过 UploadFile 接收，不在此模型中定义
    """

    file_md5: str = Field(..., min_length=32, max_length=64, description="文件MD5")
    chunk_index: int = Field(..., ge=0, description="分片索引，从0开始")
    total_chunks: int = Field(..., ge=1, description="总分片数")
    chunk_size: int = Field(..., ge=1, description="当前分片大小（字节）")
    total_size: int = Field(..., ge=1, description="文件总大小（字节）")
    file_name: str = Field(..., max_length=255, description="文件名称")
    content_type: str = Field(..., max_length=100, description="文件MIME类型")
    is_public: bool = Field(False, description="是否为公共文件：True-公共，False-私有")


class FileUploadCompleteIn(BaseModel):
    """合并完成请求模型。

    说明：
    - 由客户端在上传完所有分片后调用
    - 服务器将进行合并、MD5校验、写入 file_storage
    """

    file_md5: str = Field(..., min_length=32, max_length=64, description="文件MD5")
    total_chunks: int = Field(..., ge=1, description="总分片数")
    file_name: str = Field(..., max_length=255, description="文件名称")
    content_type: str = Field(..., max_length=100, description="文件MIME类型")
    is_public: bool = Field(False, description="是否为公共文件：True-公共，False-私有")


class FileStorageOut(FileStorageBase):
    """文件存储输出模型。

    说明：
    - 返回给前端的完整文件信息
    - 包含 id、user_id 和时间戳
    - 不包含敏感信息（如 etag）
    """

    id: int = Field(..., description="文件ID")
    user_id: int = Field(..., description="上传用户ID")
    status: int = Field(..., description="文件状态：1-可用，2-已删除，3-禁用")
    upload_time: datetime | None = Field(None, description="上传时间")
    update_time: datetime | None = Field(None, description="更新时间")
    bucket_name: str | None = Field(None, description="存储桶名称")
    object_name: str | None = Field(None, description="对象名称")
    etag: str | None = Field(None, description="文件ETag")

    # 可选：上传者信息
    uploader_name: str | None = Field(None, description="上传者姓名")

    model_config = {"from_attributes": True}


class FileListResponse(BaseModel):
    """文件列表响应模型。

    说明：
    - 用于分页返回文件列表
    - items 为当前页的文件列表
    - total 为总文件数量
    - 支持按上传时间倒序排列（最新文件在前）

    使用示例：
        ```python
        # 分页查询用户的文件列表
        response = FileListResponse(
            items=files,
            total=50,
            page=1,
            size=10
        )
        ```
    """

    items: Sequence[FileStorageOut] = Field(..., description="文件列表")
    total: int = Field(..., description="总文件数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页数量")


class FileSessionRelation(BaseModel):
    """文件与会话关联模型。

    说明：
    - 用于管理文件与会话的关联关系
    - 包含 session_id 和关联时间
    """

    session_id: int = Field(..., description="会话ID")
    create_time: datetime | None = Field(None, description="关联时间")


class FileInfoWithSessions(FileStorageOut):
    """带会话信息的文件输出模型。

    说明：
    - 继承自 FileStorageOut
    - 扩展会话相关信息
    - 用于文件详情接口，返回使用该文件的会话列表
    """

    sessions: Sequence[int] = Field([], description="使用该文件的会话ID列表")
    # 说明：返回会话ID列表，前端可以单独调用会话接口获取详细信息
