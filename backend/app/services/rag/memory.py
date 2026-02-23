from __future__ import annotations

from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.crud.chat_message_crud import ChatMessageCRUD


class ConversationMemory:
    def __init__(self, db: Session | AsyncSession, history_limit: int = 8) -> None:
        self.db = db
        self.history_limit = history_limit

    async def get_recent_messages(self, session_id: int | None) -> Sequence[str]:
        if session_id is None:
            return []

        if isinstance(self.db, AsyncSession):
            messages = await ChatMessageCRUD.get_recent_messages_async(
                self.db, session_id=session_id, limit=self.history_limit
            )
        else:
            messages = ChatMessageCRUD.get_recent_messages(
                self.db, session_id=session_id, limit=self.history_limit
            )

        return [message.content for message in messages]
