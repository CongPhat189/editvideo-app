import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import agents as agents_ep
from app.repositories import agent_repository
from app.services import agent_service
from app.core.crypto import SecretDecryptError, decrypt_secret, encrypt_secret
from app.integrations import goclaw
from app.models import Agent, AppUser
from app.schemas.agent import (
    AgentCreate,
    AgentDetailOut,
    AgentOut,
    AgentTestConnectionIn,
    AgentTestConnectionOut,
    AgentUpdate,
)


import inspect


def run_async(coro):
    """Chạy coroutine đồng bộ trong test mà không cần socket/loopback trên Windows."""
    val = None
    stack = [coro]
    while stack:
        try:
            nxt = stack[-1].send(val)
            if inspect.iscoroutine(nxt):
                stack.append(nxt)
                val = None
            elif hasattr(nxt, "__await__"):
                stack.append(nxt.__await__())
                val = None
            else:
                val = nxt
        except StopIteration as e:
            stack.pop()
            val = e.value
    return val


# ==================== 1. Crypto & Key Masking Tests ====================

def test_encrypt_and_decrypt_secret():
    raw_key = "goclaw-live-secret-key-123456789"
    encrypted = encrypt_secret(raw_key)

    assert encrypted != raw_key
    assert isinstance(encrypted, str)
    assert decrypt_secret(encrypted) == raw_key


def test_decrypt_invalid_token_raises_error():
    with pytest.raises(SecretDecryptError):
        decrypt_secret("invalid-not-a-fernet-token")


def test_mask_key():
    # Trường hợp None
    assert agents_ep._mask_key(None) is None

    # Key ngắn (<= 8 ký tự)
    short_enc = encrypt_secret("12345")
    assert agents_ep._mask_key(short_enc) == "****"

    # Key dài
    long_key = "sk-proj-goclaw-ultra-secret-9999"
    long_enc = encrypt_secret(long_key)
    masked = agents_ep._mask_key(long_enc)

    assert masked is not None
    assert masked.startswith("sk-")
    assert masked.endswith("9999")
    assert "****" in masked
    assert "ultra-secret" not in masked

    # Ciphertext hỏng
    assert agents_ep._mask_key("corrupted_cipher") == "********"


# ==================== 2. GoClaw Target Resolution & Test Connection ====================

def test_resolve_target_decrypts_agent_key():
    raw_api_key = "sk-goclaw-agent-key-secret"
    agent = Agent(
        id=uuid.uuid4(),
        name="AI Video Director",
        domain="https://director.goclaw.ai",
        api_key=encrypt_secret(raw_api_key),
        agent_key=None,
    )

    target = goclaw.resolve_target(agent)
    assert target.agent_name == "AI Video Director"
    assert target.base_url == "https://director.goclaw.ai"


def test_goclaw_test_connection_mock():
    res = run_async(
        goclaw.test_connection(
            domain="https://api.goclaw.ai",
            api_key="sk-test-key",
            agent_key="agent-test-key",
        )
    )
    assert res["ok"] is True
    assert "Mock" in res["message"]
    assert res["details"]["domain"] == "https://api.goclaw.ai"
    assert res["details"]["has_api_key"] is True
    assert res["details"]["has_agent_key"] is True


# ==================== 3. CRUD Agent Endpoints Tests ====================

def test_create_agent_success():
    session = AsyncMock()
    user = AppUser(id=uuid.uuid4(), full_name="Hiếu", phone="+84900000001", status="active")

    payload = AgentCreate(
        name="TikTok Script Writer",
        domain="https://goclaw.creative.ai",
        api_key="sk-api-key-live-12345",
        agent_key="ag-key-live-67890",
    )

    out = run_async(agents_ep.create_agent(payload, user=user, session=session))

    assert session.add.called
    assert session.commit.called
    assert session.refresh.called

    added_agent = session.add.call_args[0][0]
    assert isinstance(added_agent, Agent)
    assert added_agent.name == "TikTok Script Writer"
    assert added_agent.domain == "https://goclaw.creative.ai"

    # API key và Agent key phải được mã hóa trong cơ sở dữ liệu
    assert added_agent.api_key != "sk-api-key-live-12345"
    assert added_agent.agent_key != "ag-key-live-67890"
    assert decrypt_secret(added_agent.api_key) == "sk-api-key-live-12345"
    assert decrypt_secret(added_agent.agent_key) == "ag-key-live-67890"

    # Output trả về cho client
    assert out.name == "TikTok Script Writer"
    assert out.domain == "https://goclaw.creative.ai"
    assert out.has_api_key is True
    assert out.has_agent_key is True
    assert "****" in out.masked_api_key
    assert "****" in out.masked_agent_key


def test_get_agent_detail_success():
    agent_id = uuid.uuid4()
    agent = Agent(
        id=agent_id,
        name="Video Subtitle Generator",
        domain="https://subtitles.goclaw.ai",
        api_key=encrypt_secret("sk-subtitles-key-9988"),
        agent_key=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session = AsyncMock()
    session.get.return_value = agent
    user = AppUser(id=uuid.uuid4(), full_name="Hiếu", phone="+84900000001", status="active")

    out = run_async(agents_ep.get_agent(agent_id, user=user, session=session))

    assert out.id == agent_id
    assert out.name == "Video Subtitle Generator"
    assert out.domain == "https://subtitles.goclaw.ai"
    assert out.has_api_key is True
    assert out.has_agent_key is False
    assert "****" in out.masked_api_key
    assert out.masked_agent_key is None


def test_get_agent_not_found():
    session = AsyncMock()
    session.get.return_value = None
    user = AppUser(id=uuid.uuid4(), full_name="Hiếu", phone="+84900000001", status="active")

    with pytest.raises(HTTPException) as exc:
        run_async(agents_ep.get_agent(uuid.uuid4(), user=user, session=session))
    assert exc.value.status_code == 404


def test_list_agents():
    user = AppUser(id=uuid.uuid4(), full_name="Hiếu", phone="+84900000001", status="active")
    session = AsyncMock()

    a1 = Agent(id=uuid.uuid4(), name="Agent A", domain="https://a.ai")
    a2 = Agent(id=uuid.uuid4(), name="Agent B", domain="https://b.ai")

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [a1, a2]
    session.scalars.return_value = mock_scalars

    res = run_async(agents_ep.list_agents(user=user, session=session))
    assert len(res) == 2
    assert res[0].name == "Agent A"
    assert res[1].name == "Agent B"


def test_update_agent_success():
    agent_id = uuid.uuid4()
    agent = Agent(
        id=agent_id,
        name="Original Name",
        domain="https://old.domain.com",
        api_key=encrypt_secret("old-key"),
        agent_key=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session = AsyncMock()
    session.get.return_value = agent
    user = AppUser(id=uuid.uuid4(), full_name="Hiếu", phone="+84900000001", status="active")

    update_data = AgentUpdate(
        name="Updated Name",
        domain="https://new.domain.com",
        api_key="new-rotated-key-12345",
    )

    out = run_async(agents_ep.update_agent(agent_id, update_data, user=user, session=session))

    assert agent.name == "Updated Name"
    assert agent.domain == "https://new.domain.com"
    assert decrypt_secret(agent.api_key) == "new-rotated-key-12345"
    assert session.commit.called
    assert out.name == "Updated Name"


def test_update_agent_not_found():
    session = AsyncMock()
    session.get.return_value = None
    user = AppUser(id=uuid.uuid4(), full_name="Hiếu", phone="+84900000001", status="active")

    with pytest.raises(HTTPException) as exc:
        run_async(agents_ep.update_agent(uuid.uuid4(), AgentUpdate(name="New"), user=user, session=session))
    assert exc.value.status_code == 404


def test_delete_agent_success():
    agent_id = uuid.uuid4()
    agent = Agent(id=agent_id, name="To Delete", domain="https://delete.ai")
    session = AsyncMock()
    session.get.return_value = agent
    user = AppUser(id=uuid.uuid4(), full_name="Hiếu", phone="+84900000001", status="active")

    res = run_async(agents_ep.delete_agent(agent_id, user=user, session=session))
    assert res["ok"] is True
    assert session.delete.called
    assert session.commit.called


def test_delete_agent_not_found():
    session = AsyncMock()
    session.get.return_value = None
    user = AppUser(id=uuid.uuid4(), full_name="Hiếu", phone="+84900000001", status="active")

    with pytest.raises(HTTPException) as exc:
        run_async(agents_ep.delete_agent(uuid.uuid4(), user=user, session=session))
    assert exc.value.status_code == 404


def test_test_agent_connection_adhoc_missing_domain():
    user = AppUser(id=uuid.uuid4(), full_name="Hiếu", phone="+84900000001", status="active")
    payload = AgentTestConnectionIn(domain="", api_key="sk-test")

    with pytest.raises(HTTPException) as exc:
        run_async(agents_ep.test_agent_connection(payload, user=user))
    assert exc.value.status_code == 400


def test_test_agent_connection_adhoc_success():
    user = AppUser(id=uuid.uuid4(), full_name="Hiếu", phone="+84900000001", status="active")
    payload = AgentTestConnectionIn(domain="https://goclaw.ai", api_key="sk-test")

    res = run_async(agents_ep.test_agent_connection(payload, user=user))
    assert res.ok is True
    assert "Mock" in res.message


def test_test_saved_agent_connection_success():
    agent_id = uuid.uuid4()
    agent = Agent(
        id=agent_id,
        name="Auto Cutter",
        domain="https://cutter.goclaw.ai",
        api_key=encrypt_secret("sk-cutter-key-1234"),
        agent_key=encrypt_secret("ag-cutter-key-5678"),
    )
    session = AsyncMock()
    session.get.return_value = agent
    user = AppUser(id=uuid.uuid4(), full_name="Hiếu", phone="+84900000001", status="active")

    res = run_async(agents_ep.test_saved_agent_connection(agent_id, user=user, session=session))
    assert res.ok is True
    assert "Mock" in res.message


# ==================== 4. 3-Tier Layer (Repository & Service) Tests ====================

def test_agent_repository_crud():
    session = AsyncMock()
    agent_id = uuid.uuid4()
    agent = Agent(id=agent_id, name="Direct Repo Agent", domain="https://repo.ai")

    # Create
    created = run_async(agent_repository.create(session, agent))
    assert session.add.called
    assert created.name == "Direct Repo Agent"

    # Get by ID
    session.get.return_value = agent
    fetched = run_async(agent_repository.get_by_id(session, agent_id))
    assert fetched.id == agent_id

    # List by User
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [agent]
    session.scalars.return_value = mock_scalars
    user_agents = run_async(agent_repository.list_by_user(session, uuid.uuid4()))
    assert len(user_agents) == 1

    # Update
    agent.name = "Updated Repo Agent"
    updated = run_async(agent_repository.update(session, agent))
    assert updated.name == "Updated Repo Agent"

    # Delete
    run_async(agent_repository.delete(session, agent))
    assert session.delete.called


def test_agent_service_delegation():
    session = AsyncMock()
    user_id = uuid.uuid4()

    payload = AgentCreate(
        name="Service Agent",
        domain="https://service.goclaw.ai",
        api_key="sk-service-key-1234",
    )

    out = run_async(agent_service.create_agent(session, user_id, payload))
    assert out.name == "Service Agent"
    assert out.user_id == user_id
    assert out.has_api_key is True
    assert "****" in out.masked_api_key


def test_list_agents_by_user_id():
    user_id = uuid.uuid4()
    agent1 = Agent(
        id=uuid.uuid4(),
        user_id=user_id,
        name="User Agent 1",
        domain="https://agent1.goclaw.ai",
        api_key=encrypt_secret("sk-key-1111"),
        agent_key=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    agent2 = Agent(
        id=uuid.uuid4(),
        user_id=user_id,
        name="User Agent 2",
        domain="https://agent2.goclaw.ai",
        api_key=None,
        agent_key=encrypt_secret("sk-agent-2222"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    session = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [agent1, agent2]
    session.scalars.return_value = mock_scalars

    # 1. Test repository get_by_user_id
    repo_results = run_async(agent_repository.get_by_user_id(session, user_id))
    assert len(repo_results) == 2
    assert repo_results[0].name == "User Agent 1"
    assert repo_results[1].name == "User Agent 2"

    # 2. Test service list_agents_by_user_id
    service_results = run_async(agent_service.list_agents_by_user_id(session, user_id))
    assert len(service_results) == 2
    assert isinstance(service_results[0], AgentDetailOut)
    assert service_results[0].user_id == user_id
    assert service_results[0].has_api_key is True
    assert service_results[0].has_agent_key is False
    assert service_results[1].has_api_key is False
    assert service_results[1].has_agent_key is True

    # 3. Test endpoint list_agents_by_user (GET /agents/user/{user_id})
    user = AppUser(id=user_id, full_name="Hiếu", phone="+84900000001", status="active")
    ep_results = run_async(agents_ep.list_agents_by_user(user_id=user_id, user=user, session=session))
    assert len(ep_results) == 2
    assert ep_results[0].name == "User Agent 1"
    assert ep_results[1].name == "User Agent 2"

    # 4. Test endpoint list_agents with query param user_id (GET /agents?user_id=...)
    ep_query_results = run_async(agents_ep.list_agents(user=user, session=session, user_id=user_id))
    assert len(ep_query_results) == 2
