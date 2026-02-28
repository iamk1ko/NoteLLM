from __future__ import annotations

import asyncio
from fastapi import FastAPI

from app.consumers.file_merge_listener import start_file_merge_listener
from app.consumers.vectorize_listener import start_vectorize_listener
from app.consumers.chat_memory_listener import start_chat_memory_listener


def start_all_listeners(app: FastAPI) -> tuple[asyncio.Task[None], ...]:
    return (
        start_file_merge_listener(app),
        start_vectorize_listener(app),
        start_chat_memory_listener(app),
    )
