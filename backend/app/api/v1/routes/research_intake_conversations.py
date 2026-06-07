from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.research_intake_conversations import service
from app.modules.research_intake_conversations.schemas import (
    ResearchIntakeConversationConfirmRead,
    ResearchIntakeConversationCreate,
    ResearchIntakeConversationRead,
    ResearchIntakeMessageCreate,
)

router = APIRouter(prefix="/research-intake-conversations")


@router.post(
    "",
    response_model=ResearchIntakeConversationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_research_intake_conversation(
    payload: ResearchIntakeConversationCreate,
    db: Session = Depends(get_db),
) -> ResearchIntakeConversationRead:
    return service.create_conversation(db, payload)


@router.get("/{conversation_uuid}", response_model=ResearchIntakeConversationRead)
def get_research_intake_conversation(
    conversation_uuid: UUID,
    db: Session = Depends(get_db),
) -> ResearchIntakeConversationRead:
    conversation = service.get_conversation(db, conversation_uuid)

    if conversation is None:
        raise HTTPException(status_code=404, detail="Research intake not found")

    return conversation


@router.post("/{conversation_uuid}/messages", response_model=ResearchIntakeConversationRead)
def add_research_intake_message(
    conversation_uuid: UUID,
    payload: ResearchIntakeMessageCreate,
    db: Session = Depends(get_db),
) -> ResearchIntakeConversationRead:
    conversation = service.add_user_message(db, conversation_uuid, payload)

    if conversation is None:
        raise HTTPException(status_code=404, detail="Research intake not found")

    return conversation


@router.post("/{conversation_uuid}/analysis", response_model=ResearchIntakeConversationRead)
def update_research_intake_requirements(
    conversation_uuid: UUID,
    db: Session = Depends(get_db),
) -> ResearchIntakeConversationRead:
    conversation = service.update_conversation_requirements(db, conversation_uuid)

    if conversation is None:
        raise HTTPException(status_code=404, detail="Research intake not found")

    return conversation


@router.post(
    "/{conversation_uuid}/confirm",
    response_model=ResearchIntakeConversationConfirmRead,
)
def confirm_research_intake_conversation(
    conversation_uuid: UUID,
    db: Session = Depends(get_db),
) -> ResearchIntakeConversationConfirmRead:
    try:
        result = service.confirm_conversation(db, conversation_uuid)
    except service.ConversationNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "missing_fields": exc.missing_fields,
            },
        ) from exc

    if result is None:
        raise HTTPException(status_code=404, detail="Research intake not found")

    return result
