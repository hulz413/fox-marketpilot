from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.research_intake_conversations.models import (
    ResearchIntakeConversation,
    ResearchIntakeMessage,
)


def create_conversation(
    db: Session,
    conversation: ResearchIntakeConversation,
) -> ResearchIntakeConversation:
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def save_conversation(
    db: Session,
    conversation: ResearchIntakeConversation,
) -> ResearchIntakeConversation:
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_active_conversation_by_uuid(
    db: Session,
    conversation_uuid: UUID,
) -> Optional[ResearchIntakeConversation]:
    statement = select(ResearchIntakeConversation).where(
        ResearchIntakeConversation.uuid == conversation_uuid,
        ResearchIntakeConversation.deleted_at.is_(None),
    )

    return db.execute(statement).scalar_one_or_none()


def add_message(
    db: Session,
    message: ResearchIntakeMessage,
    *,
    commit: bool = True,
) -> ResearchIntakeMessage:
    db.add(message)
    if commit:
        db.commit()
        db.refresh(message)
    return message


def list_active_messages(
    db: Session,
    conversation_id: int,
) -> list[ResearchIntakeMessage]:
    statement = (
        select(ResearchIntakeMessage)
        .where(
            ResearchIntakeMessage.conversation_id == conversation_id,
            ResearchIntakeMessage.deleted_at.is_(None),
        )
        .order_by(
            ResearchIntakeMessage.created_at.asc(),
            ResearchIntakeMessage.id.asc(),
        )
    )

    return list(db.execute(statement).scalars().all())
