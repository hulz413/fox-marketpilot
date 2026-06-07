from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.opportunities.models import Opportunity
from app.modules.research_intake_conversations.models import (
    ResearchIntakeConversation,
)
from app.modules.research_intake_conversations import service as intake_service
from app.modules.research_intake_conversations.service import (
    ResearchIntakeDraft,
    evaluate_readiness,
    fallback_analysis,
)
from app.modules.research_tasks import service as research_task_service
from app.modules.research_tasks.models import ResearchTask


@pytest.fixture()
def client() -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Iterator[Session]:
        db = testing_session_local()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client, testing_session_local

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_create_empty_intake_conversation(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, _ = client

    response = test_client.post("/api/v1/research-intake-conversations", json={})

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["uuid"])
    assert "id" not in body
    assert body["status"] == "active"
    assert body["draft"]["brief"] is None
    assert body["missing_fields"] == []
    assert body["assumptions"] == []
    assert body["can_create_task"] is False
    assert body["messages"] == []
    assert body["research_task_uuid"] is None


def test_fallback_analysis_normalizes_draft_and_readiness() -> None:
    conversation = ResearchIntakeConversation(
        draft_payload={},
        missing_fields=[],
        assumptions=[],
        readiness_status="needs_clarification",
        can_create_task=False,
    )

    analysis = fallback_analysis(
        conversation,
        "预算 5000 元以内，从 1688 找适合小红书种草的产品，不做食品和电子产品。",
    )

    assert analysis.can_create_task is True
    assert analysis.readiness_status == "ready"
    assert analysis.draft_update.brief
    assert analysis.draft_update.budget == "预算 5000 元以内"
    assert analysis.draft_update.target_channels == ["小红书"]
    assert analysis.draft_update.supply_preferences == ["1688"]
    assert analysis.draft_update.excluded_categories == ["食品和电子产品"]
    assert "市场" in analysis.assistant_message


def test_draft_accepts_numeric_llm_string_fields() -> None:
    draft = ResearchIntakeDraft.model_validate(
        {
            "budget": 5000,
            "expected_profit": 30,
        }
    )

    assert draft.budget == "5000"
    assert draft.expected_profit == "30"


def test_readiness_requires_core_brief() -> None:
    readiness = evaluate_readiness(ResearchIntakeDraft(), [])

    assert readiness.can_create_task is False
    assert readiness.readiness_status == "needs_clarification"
    assert readiness.missing_fields == ["brief"]
    assert "预算未指定" in readiness.assumptions[0]


def test_message_saves_conversation_without_updating_draft(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client

    response = test_client.post(
        "/api/v1/research-intake-conversations",
        json={
            "message": "预算 5000 元以内，从 1688 找适合小红书种草的产品，不做食品和电子产品。"
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["can_create_task"] is False
    assert body["readiness_status"] == "needs_clarification"
    assert body["draft"]["brief"] is None
    assert body["draft"]["budget"] is None
    assert body["draft"]["target_channels"] == []
    assert len(body["messages"]) == 2
    assert [message["role"] for message in body["messages"]] == ["user", "assistant"]
    assert "id" not in body["messages"][0]
    assert body["messages"][1]["structured_delta"] == {}
    assert body["messages"][1]["suggested_replies"]
    assert "更新需求" not in body["messages"][1]["content"]
    assert "已记录" not in body["messages"][1]["content"]
    assert "先确认" in body["messages"][1]["content"]

    with session_factory() as db:
        task_count = db.execute(select(func.count(ResearchTask.id))).scalar_one()
        opportunity_count = db.execute(select(func.count(Opportunity.id))).scalar_one()

    assert task_count == 0
    assert opportunity_count == 0


def test_suggested_replies_only_show_for_follow_up_questions() -> None:
    assert intake_service.suggested_replies_for_assistant(
        "另外，预算大概在什么范围？"
    ) == ["3000 元内", "5000 元内", "先不限定"]

    assert (
        intake_service.suggested_replies_for_assistant(
            "可以，当前信息已经够启动一次基础研究；如果还想补充供给方式、目标人群或限制条件，可以继续告诉我。"
        )
        == []
    )


def test_message_uses_fallback_when_llm_returns_invalid_analysis(
    client: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, _ = client

    class FakeMessage:
        content = '{"required_output": {"can_create_task": false}}'

    class FakeChoice:
        message = FakeMessage()

    class FakeCompletions:
        def create(self, **_: object) -> object:
            return type("FakeCompletion", (), {"choices": [FakeChoice()]})()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setenv("LLM_API_KEY", "test-key")
    intake_service.get_settings.cache_clear()
    monkeypatch.setattr(intake_service, "create_llm_client", lambda: FakeClient())

    response = test_client.post(
        "/api/v1/research-intake-conversations",
        json={"message": "找适合社群团购的宠物清洁用品，首批验证预算控制在 3000 元内。"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["error_summary"] is None
    assert body["draft"]["brief"] is None
    assert [message["role"] for message in body["messages"]] == ["user", "assistant"]
    assert body["messages"][-1]["structured_delta"] == {}
    assert "需求追问暂时失败" not in body["messages"][-1]["content"]
    assert "required_output" not in body["messages"][-1]["content"]
    assert "已记录" not in body["messages"][-1]["content"]

    intake_service.get_settings.cache_clear()


def test_message_uses_fallback_when_llm_only_acknowledges(
    client: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, _ = client

    class FakeMessage:
        content = "好的"

    class FakeChoice:
        message = FakeMessage()

    class FakeCompletions:
        def create(self, **_: object) -> object:
            return type("FakeCompletion", (), {"choices": [FakeChoice()]})()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setenv("LLM_API_KEY", "test-key")
    intake_service.get_settings.cache_clear()
    monkeypatch.setattr(intake_service, "create_llm_client", lambda: FakeClient())

    response = test_client.post(
        "/api/v1/research-intake-conversations",
        json={"message": "面向租房办公人群，寻找低库存、可内容种草的桌面小物。"},
    )

    assert response.status_code == 201
    assistant_content = response.json()["messages"][-1]["content"]
    assert assistant_content != "好的"
    assert "预算" in assistant_content or "渠道" in assistant_content

    intake_service.get_settings.cache_clear()


def test_chat_follow_up_keeps_asking_after_short_user_reply(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, _ = client
    created = test_client.post(
        "/api/v1/research-intake-conversations",
        json={"message": "面向租房办公人群，寻找低库存、可内容种草的桌面小物。"},
    ).json()

    response = test_client.post(
        f"/api/v1/research-intake-conversations/{created['uuid']}/messages",
        json={"content": "先拿样品"},
    )

    assert response.status_code == 200
    body = response.json()
    assistant_content = body["messages"][-1]["content"]
    assert assistant_content != "好的"
    assert "预算" in assistant_content or "渠道" in assistant_content
    assert "先拿样品" in body["messages"][-2]["content"]
    assert body["draft"]["brief"] is None


def test_update_requirements_updates_draft_without_creating_task(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created = test_client.post(
        "/api/v1/research-intake-conversations",
        json={
            "message": "预算 5000 元以内，从 1688 找适合小红书种草的产品，不做食品和电子产品。"
        },
    ).json()

    response = test_client.post(
        f"/api/v1/research-intake-conversations/{created['uuid']}/analysis"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["can_create_task"] is True
    assert body["readiness_status"] == "ready"
    assert body["draft"]["brief"].startswith("预算 5000 元以内")
    assert body["draft"]["budget"] == "预算 5000 元以内"
    assert body["draft"]["target_channels"] == ["小红书"]
    assert len(body["messages"]) == 3
    assert [message["role"] for message in body["messages"]] == [
        "user",
        "assistant",
        "assistant",
    ]
    assert body["messages"][-1]["structured_delta"]["target_channels"] == ["小红书"]

    with session_factory() as db:
        task_count = db.execute(select(func.count(ResearchTask.id))).scalar_one()
        opportunity_count = db.execute(select(func.count(Opportunity.id))).scalar_one()

    assert task_count == 0
    assert opportunity_count == 0


def test_update_requirements_uses_fallback_when_llm_times_out(
    client: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, _ = client
    calls: list[dict[str, object]] = []

    class FakeCompletions:
        def create(self, **kwargs: object) -> object:
            calls.append(kwargs)
            raise TimeoutError("slow model")

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setenv("LLM_API_KEY", "test-key")
    intake_service.get_settings.cache_clear()
    monkeypatch.setattr(intake_service, "create_llm_client", lambda: FakeClient())

    created = test_client.post(
        "/api/v1/research-intake-conversations",
        json={
            "message": "预算 5000 元以内，从 1688 找适合小红书种草的产品，不做食品和电子产品。"
        },
    ).json()

    response = test_client.post(
        f"/api/v1/research-intake-conversations/{created['uuid']}/analysis"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["error_summary"] is None
    assert body["can_create_task"] is True
    assert body["draft"]["budget"] == "预算 5000 元以内"
    assert any(
        call.get("response_format") == {"type": "json_object"}
        and call.get("timeout") == intake_service.INTAKE_ANALYSIS_TIMEOUT_SECONDS
        for call in calls
    )

    intake_service.get_settings.cache_clear()


def test_update_intent_message_updates_requirements_without_follow_up(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, _ = client
    created = test_client.post(
        "/api/v1/research-intake-conversations",
        json={
            "message": "预算 5000 元以内，从 1688 找适合小红书种草的产品，不做食品和电子产品。"
        },
    ).json()

    response = test_client.post(
        f"/api/v1/research-intake-conversations/{created['uuid']}/messages",
        json={"content": "信息差不多够了，先更新需求吧"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["can_create_task"] is True
    assert body["draft"]["budget"] == "预算 5000 元以内"
    assert body["draft"]["target_channels"] == ["小红书"]
    assert body["messages"][-2]["role"] == "user"
    assert body["messages"][-2]["content"] == "信息差不多够了，先更新需求吧"
    assert body["messages"][-1]["role"] == "assistant"
    assert body["messages"][-1]["structured_delta"]["budget"] == "预算 5000 元以内"
    assert "先确认" not in body["messages"][-1]["content"]


def test_follow_up_message_updates_channel_without_replacing_brief(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, _ = client
    first_brief = "面向租房办公人群，寻找低库存、可内容种草的桌面小物。"
    created = test_client.post(
        "/api/v1/research-intake-conversations",
        json={"message": first_brief},
    ).json()
    analyzed = test_client.post(
        f"/api/v1/research-intake-conversations/{created['uuid']}/analysis"
    ).json()

    saved = test_client.post(
        f"/api/v1/research-intake-conversations/{analyzed['uuid']}/messages",
        json={"content": "渠道通过咸鱼？"},
    )

    assert saved.status_code == 200
    saved_body = saved.json()
    assert saved_body["draft"]["target_channels"] == []
    assert [message["role"] for message in saved_body["messages"][-2:]] == [
        "user",
        "assistant",
    ]
    assert saved_body["messages"][-1]["structured_delta"] == {}

    response = test_client.post(
        f"/api/v1/research-intake-conversations/{analyzed['uuid']}/analysis"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["draft"]["brief"] == first_brief
    assert body["draft"]["target_channels"] == ["闲鱼"]
    assert body["messages"][-1]["role"] == "assistant"
    assert "目标渠道：闲鱼" not in body["messages"][-1]["content"]
    assert "已更新" not in body["messages"][-1]["content"]
    assert body["messages"][-1]["structured_delta"]["target_channels"] == ["闲鱼"]


def test_confirm_not_ready_conversation_returns_missing_fields(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created = test_client.post("/api/v1/research-intake-conversations", json={}).json()

    response = test_client.post(
        f"/api/v1/research-intake-conversations/{created['uuid']}/confirm"
    )

    assert response.status_code == 409
    assert response.json()["detail"]["missing_fields"] == ["brief"]
    with session_factory() as db:
        assert db.execute(select(func.count(ResearchTask.id))).scalar_one() == 0


def test_confirm_conversation_creates_and_starts_task_once(
    client: tuple[TestClient, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, session_factory = client
    enqueued_runs: list[tuple[UUID, str]] = []

    def fake_enqueue(task_uuid: UUID, run_id: str) -> None:
        enqueued_runs.append((task_uuid, run_id))

    monkeypatch.setattr(research_task_service, "enqueue_research_run", fake_enqueue)

    created = test_client.post(
        "/api/v1/research-intake-conversations",
        json={
            "message": "预算 5000 元以内，从 1688 找适合小红书种草的产品，不做食品和电子产品。"
        },
    ).json()
    analyzed = test_client.post(
        f"/api/v1/research-intake-conversations/{created['uuid']}/analysis"
    ).json()

    response = test_client.post(
        f"/api/v1/research-intake-conversations/{analyzed['uuid']}/confirm"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["research_task_uuid"]
    assert body["conversation"]["status"] == "converted"
    assert body["conversation"]["research_task_uuid"] == body["research_task_uuid"]
    assert body["error_summary"] is None
    assert len(enqueued_runs) == 1

    repeat_response = test_client.post(
        f"/api/v1/research-intake-conversations/{analyzed['uuid']}/confirm"
    )

    assert repeat_response.status_code == 200
    assert repeat_response.json()["research_task_uuid"] == body["research_task_uuid"]
    assert len(enqueued_runs) == 1

    task_response = test_client.get(
        f"/api/v1/research-tasks/{body['research_task_uuid']}"
    )
    assert task_response.status_code == 200
    assert task_response.json()["status"] == "queued"
    assert task_response.json()["budget"] == "预算 5000 元以内"
    assert task_response.json()["target_channels"] == ["小红书"]

    with session_factory() as db:
        assert db.execute(select(func.count(ResearchTask.id))).scalar_one() == 1


def test_get_missing_and_soft_deleted_conversation_returns_404(
    client: tuple[TestClient, sessionmaker[Session]],
) -> None:
    test_client, session_factory = client
    created = test_client.post("/api/v1/research-intake-conversations", json={}).json()

    assert (
        test_client.get(f"/api/v1/research-intake-conversations/{uuid4()}").status_code
        == 404
    )

    with session_factory() as db:
        conversation = db.execute(
            select(ResearchIntakeConversation).where(
                ResearchIntakeConversation.uuid == UUID(created["uuid"])
            )
        ).scalar_one()
        conversation.deleted_at = datetime.now(timezone.utc)
        db.commit()

    response = test_client.get(
        f"/api/v1/research-intake-conversations/{created['uuid']}"
    )
    assert response.status_code == 404
