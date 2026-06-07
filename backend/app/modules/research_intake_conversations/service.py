from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.integrations.langsmith import langsmith_trace
from app.integrations.llm import create_llm_client
from app.modules.research_intake_conversations import repository
from app.modules.research_intake_conversations.models import (
    ResearchIntakeConversation,
    ResearchIntakeMessage,
)
from app.modules.research_intake_conversations.schemas import (
    ResearchIntakeConversationConfirmRead,
    ResearchIntakeConversationCreate,
    ResearchIntakeConversationRead,
    ResearchIntakeConversationStatus,
    ResearchIntakeDraft,
    ResearchIntakeMessageCreate,
    ResearchIntakeMessageRead,
    ResearchIntakeMessageRole,
    ResearchIntakeReadinessStatus,
)
from app.modules.research_tasks import service as research_tasks_service
from app.modules.research_tasks.schemas import ResearchTaskCreate, ResearchTaskStatus

logger = logging.getLogger(__name__)

DEFAULT_CHANNEL_ASSUMPTION = "默认按中文内容平台进行初步研究。"
DEFAULT_BUDGET_ASSUMPTION = "预算未指定，后续研究按小预算验证思路处理。"
DEFAULT_EXCLUSION_ASSUMPTION = "默认暂无特别排除品类，结果仍需人工确认。"
CHAT_FOLLOW_UP_TIMEOUT_SECONDS = 4.0
INTAKE_ANALYSIS_TIMEOUT_SECONDS = 8.0

LIST_SPLIT_PATTERN = re.compile(r"[,，、\n；;]")
FOLLOW_UP_MARKERS = ("预算", "渠道", "平台", "人群", "品类", "排除", "不做", "不要", "供给", "货源", "利润")
ACKNOWLEDGEMENT_REPLIES = {
    "好",
    "好的",
    "可以",
    "可以的",
    "行",
    "收到",
    "明白",
    "了解",
    "ok",
}
UPDATE_REQUIREMENTS_INTENT_MARKERS = (
    "更新需求",
    "整理需求",
    "更新一下需求",
    "整理一下需求",
    "生成草稿",
    "整理成草稿",
    "信息够了",
    "信息差不多",
    "差不多了",
    "先更新",
    "先整理",
)
UPDATE_REQUIREMENTS_NEGATION_MARKERS = (
    "不要更新需求",
    "别更新需求",
    "先别更新",
    "不用更新需求",
)
UNNATURAL_CHAT_MARKERS = (
    "已记录",
    "已更新",
    "我已记录",
    "我已更新",
    "更新需求",
    "右侧草稿",
    "草稿",
    "结构化草稿",
    "确认并启动",
)
BUDGET_PATTERN = re.compile(
    r"((?:预算|首批|验证预算)?\s*\d+(?:\.\d+)?\s*(?:元|块|万|w|W)(?:以内|以下|左右|上下)?)"
)
TARGET_AUDIENCE_PATTERN = re.compile(r"面向([^，。,.!?！？]+?)(?:，|。|,|\.|!|\?|！|？|$)")


class ConversationNotReadyError(ValueError):
    def __init__(self, message: str, missing_fields: list[str]) -> None:
        super().__init__(message)
        self.missing_fields = missing_fields


class IntakeDraftAnalysis(BaseModel):
    assistant_message: str = Field(min_length=1, max_length=1200)
    draft_update: ResearchIntakeDraft = Field(default_factory=ResearchIntakeDraft)
    missing_fields: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    readiness_status: ResearchIntakeReadinessStatus = (
        ResearchIntakeReadinessStatus.NEEDS_CLARIFICATION
    )
    can_create_task: bool = False


@dataclass(frozen=True)
class ReadinessResult:
    missing_fields: list[str]
    assumptions: list[str]
    readiness_status: ResearchIntakeReadinessStatus
    can_create_task: bool


def is_update_requirements_intent(content: str) -> bool:
    normalized = re.sub(r"\s+", "", content.strip().lower())
    if not normalized:
        return False
    if any(marker in normalized for marker in UPDATE_REQUIREMENTS_NEGATION_MARKERS):
        return False
    return any(marker in normalized for marker in UPDATE_REQUIREMENTS_INTENT_MARKERS)


def create_conversation(
    db: Session,
    payload: ResearchIntakeConversationCreate,
) -> ResearchIntakeConversationRead:
    conversation = repository.create_conversation(
        db,
        ResearchIntakeConversation(
            status=ResearchIntakeConversationStatus.ACTIVE.value,
            draft_payload=ResearchIntakeDraft().model_dump(mode="json"),
            missing_fields=[],
            assumptions=[],
            readiness_status=ResearchIntakeReadinessStatus.NEEDS_CLARIFICATION.value,
            can_create_task=False,
        ),
    )

    if payload.message:
        return add_user_message(
            db,
            conversation.uuid,
            ResearchIntakeMessageCreate(content=payload.message),
        )

    return conversation_to_read(db, conversation)


def get_conversation(
    db: Session,
    conversation_uuid: UUID,
) -> Optional[ResearchIntakeConversationRead]:
    conversation = repository.get_active_conversation_by_uuid(db, conversation_uuid)

    if conversation is None:
        return None

    return conversation_to_read(db, conversation)


def add_user_message(
    db: Session,
    conversation_uuid: UUID,
    payload: ResearchIntakeMessageCreate,
) -> Optional[ResearchIntakeConversationRead]:
    conversation = repository.get_active_conversation_by_uuid(db, conversation_uuid)

    if conversation is None:
        return None

    if conversation.status == ResearchIntakeConversationStatus.CONVERTED.value:
        conversation.error_summary = "该对话已经创建研究任务，可以直接查看任务进度。"
        return conversation_to_read(db, repository.save_conversation(db, conversation))

    repository.add_message(
        db,
        ResearchIntakeMessage(
            conversation_id=conversation.id,
            role=ResearchIntakeMessageRole.USER.value,
            content=payload.content,
            structured_delta={},
            processing_metadata={"stage": "receive_user_message"},
        ),
        commit=False,
    )
    db.flush()

    if is_update_requirements_intent(payload.content):
        return update_conversation_requirements(db, conversation.uuid)

    started_at = perf_counter()
    try:
        messages = repository.list_active_messages(db, conversation.id)
        assistant_content = generate_chat_follow_up(
            db,
            conversation,
            payload.content,
            messages,
        )
        conversation.error_summary = None
        processing_metadata = {
            "stage": "respond_research_intake_message",
            "status": "completed",
            "duration_ms": int((perf_counter() - started_at) * 1000),
        }
    except Exception:
        logger.exception(
            "Failed to respond to research intake message",
            extra={
                "conversation_uuid": str(conversation.uuid),
                "stage": "respond_research_intake_message",
            },
        )
        conversation.error_summary = None
        processing_metadata = {
            "stage": "respond_research_intake_message",
            "status": "fallback",
            "duration_ms": int((perf_counter() - started_at) * 1000),
        }
        assistant_content = fallback_chat_follow_up(
            conversation,
            payload.content,
            repository.list_active_messages(db, conversation.id),
        )

    repository.add_message(
        db,
        ResearchIntakeMessage(
            conversation_id=conversation.id,
            role=ResearchIntakeMessageRole.ASSISTANT.value,
            content=assistant_content,
            structured_delta={},
            processing_metadata=processing_metadata,
        ),
        commit=False,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    logger.info(
        "Processed research intake chat message",
        extra={
            "conversation_uuid": str(conversation.uuid),
            "stage": "respond_research_intake_message",
            "status": processing_metadata["status"],
            "duration_ms": processing_metadata["duration_ms"],
        },
    )

    return conversation_to_read(db, conversation)


def update_conversation_requirements(
    db: Session,
    conversation_uuid: UUID,
) -> Optional[ResearchIntakeConversationRead]:
    conversation = repository.get_active_conversation_by_uuid(db, conversation_uuid)

    if conversation is None:
        return None

    if conversation.status == ResearchIntakeConversationStatus.CONVERTED.value:
        conversation.error_summary = "该对话已经创建研究任务，可以直接查看任务进度。"
        return conversation_to_read(db, repository.save_conversation(db, conversation))

    messages = repository.list_active_messages(db, conversation.id)
    user_messages = [
        message for message in messages if message.role == ResearchIntakeMessageRole.USER.value
    ]
    analysis_user_messages = [
        message
        for message in user_messages
        if not is_update_requirements_intent(message.content)
    ]
    if not analysis_user_messages:
        conversation.error_summary = "请先发送一条研究需求。"
        return conversation_to_read(db, repository.save_conversation(db, conversation))

    started_at = perf_counter()
    analysis_content = build_analysis_content(analysis_user_messages)

    try:
        analysis = analyze_intake_message(
            db,
            conversation,
            analysis_content,
        )
        apply_analysis_to_conversation(conversation, analysis)
        conversation.error_summary = None
        processing_metadata = {
            "stage": "update_research_intake_requirements",
            "status": "completed",
            "duration_ms": int((perf_counter() - started_at) * 1000),
            "user_message_count": len(analysis_user_messages),
        }
        assistant_content = build_update_assistant_message(
            conversation,
            analysis,
            analysis_content,
        )
        structured_delta = analysis.draft_update.model_dump(mode="json")
    except Exception:
        logger.exception(
            "Failed to analyze research intake message",
            extra={
                "conversation_uuid": str(conversation.uuid),
                "stage": "update_research_intake_requirements",
            },
        )
        conversation.error_summary = "需求整理暂时失败，请换一种方式补充条件或稍后重试。"
        conversation.can_create_task = False
        conversation.readiness_status = (
            ResearchIntakeReadinessStatus.NEEDS_CLARIFICATION.value
        )
        processing_metadata = {
            "stage": "update_research_intake_requirements",
            "status": "failed",
            "duration_ms": int((perf_counter() - started_at) * 1000),
            "user_message_count": len(analysis_user_messages),
            "error_summary": conversation.error_summary,
        }
        assistant_content = conversation.error_summary
        structured_delta = {}

    repository.add_message(
        db,
        ResearchIntakeMessage(
            conversation_id=conversation.id,
            role=ResearchIntakeMessageRole.ASSISTANT.value,
            content=assistant_content,
            structured_delta=structured_delta,
            processing_metadata=processing_metadata,
        ),
        commit=False,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    logger.info(
        "Processed research intake message",
        extra={
            "conversation_uuid": str(conversation.uuid),
            "stage": "update_research_intake_requirements",
            "status": processing_metadata["status"],
            "duration_ms": processing_metadata["duration_ms"],
        },
    )

    return conversation_to_read(db, conversation)


def build_analysis_content(user_messages: list[ResearchIntakeMessage]) -> str:
    return "\n".join(
        message.content
        for message in user_messages
        if message.content and not is_update_requirements_intent(message.content)
    )


def confirm_conversation(
    db: Session,
    conversation_uuid: UUID,
) -> Optional[ResearchIntakeConversationConfirmRead]:
    conversation = repository.get_active_conversation_by_uuid(db, conversation_uuid)

    if conversation is None:
        return None

    if conversation.research_task_id:
        task = research_tasks_service.get_research_task_by_id(
            db,
            conversation.research_task_id,
        )
        return ResearchIntakeConversationConfirmRead(
            conversation=conversation_to_read(db, conversation),
            research_task_uuid=task.uuid if task else None,
            error_summary=conversation.error_summary,
        )

    draft = draft_from_payload(conversation.draft_payload)
    readiness = evaluate_readiness(draft, conversation.assumptions)
    if not readiness.can_create_task:
        conversation.missing_fields = readiness.missing_fields
        conversation.assumptions = readiness.assumptions
        conversation.can_create_task = False
        conversation.readiness_status = readiness.readiness_status.value
        conversation.error_summary = "请先补充核心研究需求后再启动。"
        repository.save_conversation(db, conversation)
        raise ConversationNotReadyError(
            conversation.error_summary,
            readiness.missing_fields,
        )

    task_payload = ResearchTaskCreate(
        brief=draft.brief or "",
        budget=draft.budget,
        target_channels=draft.target_channels,
        preferred_categories=draft.preferred_categories,
        excluded_categories=draft.excluded_categories,
        target_audience=draft.target_audience,
        expected_profit=draft.expected_profit,
        supply_preferences=draft.supply_preferences,
        constraints=draft.constraints,
    )
    task = research_tasks_service.create_research_task(db, task_payload)
    started_task = research_tasks_service.start_research_run(db, task.uuid)

    conversation.status = ResearchIntakeConversationStatus.CONVERTED.value
    conversation.research_task_id = task.id
    if started_task and started_task.status == ResearchTaskStatus.FAILED.value:
        conversation.error_summary = (
            started_task.failure_reason
            or "任务已创建，但启动研究失败，请稍后从进度页重新运行。"
        )
    else:
        conversation.error_summary = None
    repository.save_conversation(db, conversation)

    logger.info(
        "Converted research intake conversation",
        extra={
            "conversation_uuid": str(conversation.uuid),
            "research_task_uuid": str(task.uuid),
            "stage": "confirm_research_intake",
            "status": "completed" if conversation.error_summary is None else "partial",
        },
    )

    return ResearchIntakeConversationConfirmRead(
        conversation=conversation_to_read(db, conversation),
        research_task_uuid=task.uuid,
        error_summary=conversation.error_summary,
    )


def generate_chat_follow_up(
    db: Session,
    conversation: ResearchIntakeConversation,
    user_content: str,
    messages: list[ResearchIntakeMessage] | None = None,
) -> str:
    settings = get_settings()
    messages = messages or repository.list_active_messages(db, conversation.id)[-8:]
    if not settings.llm_api_key and settings.environment in {"local", "test"}:
        return fallback_chat_follow_up(conversation, user_content, messages)

    if not settings.llm_api_key:
        return fallback_chat_follow_up(conversation, user_content, messages)

    prompt_messages = [
        {
            "role": "system",
            "content": (
                "你是 MarketPilot 的商机需求顾问。像正常聊天一样帮用户澄清需求，"
                "每次最多追问两个问题。不要说已记录、已更新、我已整理、右侧草稿、"
                "结构化草稿、更新需求、确认并启动。不要声称完成市场、供给、竞品或来源核验。"
                "不要复述用户已经说过的条件。回复要短，直接推进下一步。"
                "只要仍缺少预算、渠道、人群、品类、排除条件或供给偏好，就必须继续追问。"
                "不能只回复好的、收到、明白、可以。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "recent_messages": [
                        {"role": message.role, "content": message.content}
                        for message in messages
                    ],
                    "latest_user_message": user_content,
                    "style": "自然中文聊天，不输出 JSON",
                },
                ensure_ascii=False,
            ),
        },
    ]

    with langsmith_trace(
        "research_intake_chat_follow_up",
        inputs={
            "conversation_uuid": str(conversation.uuid),
            "message_count": len(messages),
        },
        metadata={"capability": "research-intake-conversations"},
    ) as trace_context:
        completion = create_llm_client().chat.completions.create(
            model=settings.llm_model,
            messages=prompt_messages,
            max_tokens=220,
            temperature=0.2,
            timeout=CHAT_FOLLOW_UP_TIMEOUT_SECONDS,
        )
        if trace_context:
            conversation.trace_id = trace_context.trace_id
            conversation.trace_url = trace_context.trace_url

    content = sanitize_chat_follow_up(completion.choices[0].message.content or "")
    if is_unusable_chat_follow_up(content):
        return fallback_chat_follow_up(conversation, user_content, messages)

    return content


def sanitize_chat_follow_up(content: str) -> str:
    cleaned = content.strip()
    cleaned = re.sub(r"^商机顾问[:：]\s*", "", cleaned)
    cleaned = re.sub(r"^(好的|明白|了解|收到)[，,][^。！？]*[。！？]\s*", "", cleaned)
    cleaned = re.sub(r"^好的[，,]\s*", "", cleaned)
    return cleaned


def is_unusable_chat_follow_up(content: str) -> bool:
    if not content or content.startswith(("{", "[")):
        return True
    if "required_output" in content or "draft_update" in content:
        return True
    if is_acknowledgement_only(content):
        return True
    return any(marker in content for marker in UNNATURAL_CHAT_MARKERS)


def is_acknowledgement_only(content: str) -> bool:
    normalized = re.sub(r"[\s。.!！?？,，、~～]+", "", content).lower()
    return normalized in ACKNOWLEDGEMENT_REPLIES


def build_update_assistant_message(
    conversation: ResearchIntakeConversation,
    analysis: IntakeDraftAnalysis,
    user_content: str,
) -> str:
    if analysis.can_create_task:
        return (
            "可以，当前信息已经够启动一次基础研究；如果还想补充供给方式、"
            "目标人群或限制条件，可以继续告诉我。"
        )

    content = sanitize_chat_follow_up(analysis.assistant_message)
    if is_unusable_chat_follow_up(content):
        return fallback_chat_follow_up(conversation, user_content)

    return content


def fallback_chat_follow_up(
    conversation: ResearchIntakeConversation,
    user_content: str,
    messages: list[ResearchIntakeMessage] | None = None,
) -> str:
    merged_draft = build_temporary_chat_draft(conversation, user_content, messages)

    questions = []
    if not merged_draft.budget:
        questions.append("预算大概在什么范围？")
    if not merged_draft.target_channels:
        questions.append("想优先在哪个渠道验证？")
    if not merged_draft.target_audience:
        questions.append("主要面向哪类人群？")
    if not merged_draft.preferred_categories:
        questions.append("偏好的产品形态或品类是什么？")
    if not merged_draft.supply_preferences:
        questions.append("希望从哪里找货，或者对供给方式有什么要求？")
    if not merged_draft.expected_profit:
        questions.append("对价格带或毛利有要求吗？")
    if not merged_draft.excluded_categories and not merged_draft.constraints:
        questions.append("有没有明确不做的品类或限制？")

    if not questions:
        return "方向已经比较清楚了。还有没有预算、渠道、人群或排除品类想补充？"

    return f"这个方向可以，先确认两点：{' '.join(questions[:2])}"


def suggested_replies_for_assistant(content: str) -> list[str]:
    if not is_follow_up_question(content):
        return []

    suggestions: list[str] = []

    def add(items: list[str]) -> None:
        for item in items:
            if item not in suggestions:
                suggestions.append(item)

    if "预算" in content:
        add(["3000 元内", "5000 元内", "先不限定"])
    if "渠道" in content or "平台" in content or "哪里验证" in content:
        add(["小红书", "社群团购", "短视频"])
    if "人群" in content or "哪类用户" in content:
        add(["养猫用户", "租房办公人群", "宝妈人群"])
    if "品类" in content or "产品形态" in content:
        add(["桌面小物", "宠物清洁用品", "收纳用品"])
    if "供给" in content or "找货" in content or "货源" in content:
        add(["1688 找货", "先拿样品", "小批量采购"])
    if "价格带" in content or "毛利" in content:
        add(["毛利 30%+", "先不限定"])
    if "排除" in content or "不做" in content or "限制" in content:
        add(["不做食品", "不做电子产品", "暂无限制"])

    return suggestions[:4]


def is_follow_up_question(content: str) -> bool:
    question_markers = (
        "?",
        "？",
        "什么",
        "多少",
        "哪些",
        "哪个",
        "哪类",
        "哪里",
        "有没有",
        "是否",
        "吗",
    )
    return any(marker in content for marker in question_markers)


def build_temporary_chat_draft(
    conversation: ResearchIntakeConversation,
    user_content: str,
    messages: list[ResearchIntakeMessage] | None = None,
) -> ResearchIntakeDraft:
    user_contents = [
        message.content
        for message in messages or []
        if message.role == ResearchIntakeMessageRole.USER.value and message.content
    ]
    if not user_contents or user_contents[-1] != user_content:
        user_contents.append(user_content)

    draft = draft_from_payload(conversation.draft_payload)
    for content in user_contents:
        draft_update = infer_draft_update(content)
        if draft.brief and should_keep_existing_brief(content, draft_update):
            draft_update.brief = None
        draft = merge_draft(draft, draft_update)

    return draft


def should_keep_existing_brief(
    user_content: str,
    draft_update: ResearchIntakeDraft,
) -> bool:
    return len(user_content.strip()) <= 80 or is_follow_up_update(
        user_content,
        draft_update,
    )


def analyze_intake_message(
    db: Session,
    conversation: ResearchIntakeConversation,
    user_content: str,
) -> IntakeDraftAnalysis:
    settings = get_settings()
    if not settings.llm_api_key and settings.environment in {"local", "test"}:
        return fallback_analysis(conversation, user_content)

    if not settings.llm_api_key:
        raise RuntimeError("LLM API key is not configured")

    messages = [
        message
        for message in repository.list_active_messages(db, conversation.id)
        if not (
            message.role == ResearchIntakeMessageRole.USER.value
            and is_update_requirements_intent(message.content)
        )
    ][-8:]
    current_draft = draft_from_payload(conversation.draft_payload)
    prompt_messages = [
        {
            "role": "system",
            "content": (
                "你是 MarketPilot 的研究需求对齐助手，只负责把用户的模糊商机想法"
                "整理为可创建研究任务的结构化草稿。不要声称完成市场调研、来源核验、"
                "供给核验或竞品核验。一次最多追问两个问题。必须返回 JSON object。"
                "只返回包含 assistant_message、draft_update、missing_fields、assumptions、"
                "readiness_status、can_create_task 这些顶层字段的 JSON object，"
                "不要回传 current_draft、recent_messages 或 required_output。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "current_draft": current_draft.model_dump(mode="json"),
                    "recent_messages": [
                        {"role": message.role, "content": message.content}
                        for message in messages
                    ],
                    "required_output": {
                        "assistant_message": "中文回复，最多两个问题；可以说明本次草稿更新内容",
                        "draft_update": {
                            "brief": "自然语言需求或 null",
                            "budget": "预算或 null",
                            "target_channels": ["渠道"],
                            "preferred_categories": ["偏好品类"],
                            "excluded_categories": ["排除品类"],
                            "target_audience": "目标人群或 null",
                            "expected_profit": "期望利润或 null",
                            "supply_preferences": ["供给偏好"],
                            "constraints": "其他限制或 null",
                        },
                        "missing_fields": ["仍需补充字段"],
                        "assumptions": ["默认假设"],
                        "readiness_status": "needs_clarification|ready",
                        "can_create_task": False,
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]

    with langsmith_trace(
        "research_intake_conversation",
        inputs={
            "conversation_uuid": str(conversation.uuid),
            "message_count": len(messages),
            "draft_keys": [
                key
                for key, value in current_draft.model_dump(mode="json").items()
                if value
            ],
        },
        metadata={"capability": "research-intake-conversations"},
    ) as trace_context:
        try:
            completion = create_llm_client().chat.completions.create(
                model=settings.llm_model,
                messages=prompt_messages,
                response_format={"type": "json_object"},
                timeout=INTAKE_ANALYSIS_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            logger.warning(
                "LLM intake analysis failed; using fallback",
                extra={
                    "conversation_uuid": str(conversation.uuid),
                    "error_type": type(exc).__name__,
                },
            )
            return fallback_analysis(conversation, user_content)
        if trace_context:
            conversation.trace_id = trace_context.trace_id
            conversation.trace_url = trace_context.trace_url

    content = completion.choices[0].message.content or ""
    try:
        raw_payload = json.loads(content)
        analysis = IntakeDraftAnalysis.model_validate(raw_payload)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning(
            "LLM returned invalid intake analysis; using fallback",
            extra={
                "conversation_uuid": str(conversation.uuid),
                "error_type": type(exc).__name__,
            },
        )
        return fallback_analysis(conversation, user_content)

    merged_draft = merge_draft(current_draft, analysis.draft_update)
    readiness = evaluate_readiness(
        merged_draft,
        [*conversation.assumptions, *analysis.assumptions],
    )

    return IntakeDraftAnalysis(
        assistant_message=analysis.assistant_message,
        draft_update=analysis.draft_update,
        missing_fields=readiness.missing_fields,
        assumptions=readiness.assumptions,
        readiness_status=readiness.readiness_status,
        can_create_task=readiness.can_create_task,
    )


def fallback_analysis(
    conversation: ResearchIntakeConversation,
    user_content: str,
) -> IntakeDraftAnalysis:
    current_draft = draft_from_payload(conversation.draft_payload)
    draft_update = infer_draft_update(user_content)
    if current_draft.brief and is_follow_up_update(user_content, draft_update):
        draft_update.brief = None
    merged_draft = merge_draft(current_draft, draft_update)
    readiness = evaluate_readiness(merged_draft, conversation.assumptions)

    if readiness.can_create_task:
        assistant_message = build_ready_assistant_message(draft_update)
    else:
        questions = []
        if "brief" in readiness.missing_fields:
            questions.append("你想研究的生意方向或产品大类是什么？")
        if "budget" in readiness.missing_fields:
            questions.append("首批验证预算大概是多少，或者先按预算未定处理？")
        if "target_channels" in readiness.missing_fields:
            questions.append("你希望优先在哪些渠道验证？")
        assistant_message = " ".join(questions[:2]) or "请再补充一点研究方向。"

    return IntakeDraftAnalysis(
        assistant_message=assistant_message,
        draft_update=draft_update,
        missing_fields=readiness.missing_fields,
        assumptions=readiness.assumptions,
        readiness_status=readiness.readiness_status,
        can_create_task=readiness.can_create_task,
    )


def infer_draft_update(user_content: str) -> ResearchIntakeDraft:
    content = user_content.strip()
    budget_match = BUDGET_PATTERN.search(content)
    target_audience_match = TARGET_AUDIENCE_PATTERN.search(content)

    target_channels = extract_known_terms(
        content,
        [
            ("小红书", "小红书"),
            ("抖音", "抖音"),
            ("短视频", "短视频"),
            ("视频号", "视频号"),
            ("社群团购", "社群团购"),
            ("社群", "社群"),
            ("淘宝", "淘宝"),
            ("闲鱼", "闲鱼"),
            ("咸鱼", "闲鱼"),
        ],
    )
    supply_preferences = extract_known_terms(
        content,
        [
            ("1688", "1688"),
            ("义乌", "义乌"),
            ("批发市场", "批发市场"),
            ("工厂", "工厂"),
            ("淘宝联盟", "淘宝联盟"),
            ("拼多多", "拼多多"),
            ("拿样", "先拿样品"),
            ("样品", "先拿样品"),
            ("小批量", "小批量采购"),
        ],
    )
    preferred_categories = extract_known_terms(
        content,
        [
            ("低库存", "低库存"),
            ("轻库存", "轻库存"),
            ("内容种草", "内容种草"),
            ("桌面", "桌面小物"),
            ("收纳", "收纳"),
            ("宠物清洁", "宠物清洁"),
            ("清洁", "清洁用品"),
        ],
    )
    excluded_categories = extract_exclusions(content)

    return ResearchIntakeDraft(
        brief=content,
        budget=budget_match.group(1).strip() if budget_match else None,
        target_channels=target_channels,
        preferred_categories=preferred_categories,
        excluded_categories=excluded_categories,
        target_audience=target_audience_match.group(1).strip()
        if target_audience_match
        else None,
        supply_preferences=supply_preferences,
    )


def extract_known_terms(content: str, terms: list[tuple[str, str]]) -> list[str]:
    values = []
    for keyword, normalized in terms:
        if keyword in content and normalized not in values:
            values.append(normalized)
    return values


def is_follow_up_update(
    user_content: str,
    draft_update: ResearchIntakeDraft,
) -> bool:
    update = draft_update.model_dump(mode="json")
    changed_keys = [
        key
        for key, value in update.items()
        if key != "brief" and (value if not isinstance(value, list) else len(value) > 0)
    ]
    return bool(changed_keys) and any(marker in user_content for marker in FOLLOW_UP_MARKERS)


def build_ready_assistant_message(draft_update: ResearchIntakeDraft) -> str:
    updated_parts = describe_draft_update(draft_update)
    prefix = (
        f"已更新{updated_parts}。"
        if updated_parts
        else "我已把你的想法整理成研究草稿。"
    )
    return (
        f"{prefix}当前会按待确认需求处理，不会在聊天阶段声称完成市场、"
        "供给或竞品核验。你可以继续补充预算、人群或排除品类，"
        "也可以直接确认并启动研究。"
    )


def describe_draft_update(draft_update: ResearchIntakeDraft) -> str:
    field_labels = {
        "budget": "验证预算",
        "target_channels": "目标渠道",
        "preferred_categories": "偏好品类",
        "excluded_categories": "排除品类",
        "target_audience": "目标人群",
        "expected_profit": "期望利润",
        "supply_preferences": "供给来源偏好",
        "constraints": "其他限制条件",
    }
    payload = draft_update.model_dump(mode="json")
    parts = []
    for key, label in field_labels.items():
        value = payload.get(key)
        if isinstance(value, list):
            if value:
                parts.append(f"{label}：{'、'.join(value)}")
        elif value:
            parts.append(f"{label}：{value}")
    return "、".join(parts)


def extract_exclusions(content: str) -> list[str]:
    exclusion_markers = ["不做", "不要", "排除", "不碰"]
    for marker in exclusion_markers:
        if marker not in content:
            continue
        tail = content.split(marker, 1)[1]
        tail = re.split(r"[。.!！?？]", tail, maxsplit=1)[0]
        items = [item.strip() for item in LIST_SPLIT_PATTERN.split(tail) if item.strip()]
        return [item[:80] for item in items if item not in {"无", "没有", "暂无"}]
    return []


def draft_from_payload(payload: dict[str, Any]) -> ResearchIntakeDraft:
    try:
        return ResearchIntakeDraft.model_validate(payload or {})
    except ValidationError:
        return ResearchIntakeDraft()


def merge_draft(
    current_draft: ResearchIntakeDraft,
    draft_update: ResearchIntakeDraft,
) -> ResearchIntakeDraft:
    current = current_draft.model_dump(mode="json")
    update = draft_update.model_dump(mode="json")

    for key, value in update.items():
        if isinstance(value, list):
            if value:
                current[key] = merge_lists(current.get(key, []), value)
        elif value:
            current[key] = value

    return ResearchIntakeDraft.model_validate(current)


def merge_lists(current: Any, update: list[str]) -> list[str]:
    values = [str(item).strip() for item in current or [] if str(item).strip()]
    for item in update:
        normalized = item.strip()
        if normalized and normalized not in values:
            values.append(normalized)
    return values


def evaluate_readiness(
    draft: ResearchIntakeDraft,
    existing_assumptions: list[str],
) -> ReadinessResult:
    assumptions = dedupe(
        [
            assumption.strip()
            for assumption in existing_assumptions
            if assumption and assumption.strip()
        ]
    )

    if not draft.budget and DEFAULT_BUDGET_ASSUMPTION not in assumptions:
        assumptions.append(DEFAULT_BUDGET_ASSUMPTION)
    if not draft.target_channels and DEFAULT_CHANNEL_ASSUMPTION not in assumptions:
        assumptions.append(DEFAULT_CHANNEL_ASSUMPTION)
    if (
        not draft.excluded_categories
        and not draft.constraints
        and DEFAULT_EXCLUSION_ASSUMPTION not in assumptions
    ):
        assumptions.append(DEFAULT_EXCLUSION_ASSUMPTION)

    missing_fields = []
    if not draft.brief:
        missing_fields.append("brief")

    can_create_task = not missing_fields
    readiness_status = (
        ResearchIntakeReadinessStatus.READY
        if can_create_task
        else ResearchIntakeReadinessStatus.NEEDS_CLARIFICATION
    )
    return ReadinessResult(
        missing_fields=missing_fields,
        assumptions=assumptions,
        readiness_status=readiness_status,
        can_create_task=can_create_task,
    )


def dedupe(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def apply_analysis_to_conversation(
    conversation: ResearchIntakeConversation,
    analysis: IntakeDraftAnalysis,
) -> None:
    current_draft = draft_from_payload(conversation.draft_payload)
    merged_draft = merge_draft(current_draft, analysis.draft_update)
    conversation.draft_payload = merged_draft.model_dump(mode="json")
    conversation.missing_fields = analysis.missing_fields
    conversation.assumptions = analysis.assumptions
    conversation.readiness_status = analysis.readiness_status.value
    conversation.can_create_task = analysis.can_create_task


def conversation_to_read(
    db: Session,
    conversation: ResearchIntakeConversation,
) -> ResearchIntakeConversationRead:
    messages = repository.list_active_messages(db, conversation.id)
    research_task_uuid = None
    if conversation.research_task_id:
        task = research_tasks_service.get_research_task_by_id(
            db,
            conversation.research_task_id,
        )
        research_task_uuid = task.uuid if task else None

    return ResearchIntakeConversationRead(
        uuid=conversation.uuid,
        status=conversation.status,
        draft=draft_from_payload(conversation.draft_payload),
        missing_fields=conversation.missing_fields,
        assumptions=conversation.assumptions,
        readiness_status=conversation.readiness_status,
        can_create_task=conversation.can_create_task,
        research_task_uuid=research_task_uuid,
        trace_id=conversation.trace_id,
        trace_url=conversation.trace_url,
        error_summary=conversation.error_summary,
        messages=[
            ResearchIntakeMessageRead(
                uuid=message.uuid,
                role=message.role,
                content=message.content,
                structured_delta=message.structured_delta,
                suggested_replies=suggested_replies_for_assistant(message.content)
                if message.role == ResearchIntakeMessageRole.ASSISTANT.value
                else [],
                created_at=message.created_at,
                updated_at=message.updated_at,
                deleted_at=message.deleted_at,
            )
            for message in messages
        ],
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        deleted_at=conversation.deleted_at,
    )
