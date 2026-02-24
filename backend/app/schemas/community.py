from __future__ import annotations
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

# --- Request Schemas ---


class PublishShareRequest(BaseModel):
    source_file_id: int = Field(..., description="Original File ID")
    session_id: int = Field(..., description="Associated Session ID (with QA history)")
    title: str = Field(..., min_length=1, max_length=255, description="Share Title")
    description: Optional[str] = Field(None, description="Share Description")
    tags: Optional[List[str]] = Field(None, description="List of tags")
    is_public_source: bool = Field(False, description="Allow downloading source file")


class LikeShareRequest(BaseModel):
    action: str = Field(
        ..., pattern="^(like|unlike)$", description="Action: like or unlike"
    )


# --- Response Schemas ---


class SharePublishResponse(BaseModel):
    share_id: int
    publish_time: datetime


class CommunityItem(BaseModel):
    id: int
    title: str
    description: Optional[str]
    tags: Optional[List[str]]
    user_id: int
    user_name: str
    view_count: int
    like_count: int
    fork_count: int
    create_time: datetime
    is_liked: bool


class CommunityListResponse(BaseModel):
    items: List[CommunityItem]
    total: int
    page: int
    size: int


class ForkShareResponse(BaseModel):
    new_file_id: int
    new_session_id: int


class LikeShareResponse(BaseModel):
    success: bool
    like_count: int
