from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from ollama import RequestError

from agents import agent
from app.main import app
from app.security import CurrentUser, get_current_user
from controllers.agent_controller import chat_service

client = TestClient(app)
USER_ID = "11111111-2222-3333-4444-555555555555"


@pytest.fixture
def authenticated_user():
    user = CurrentUser(
        id=USER_ID,
        email="ana@eia.edu.co",
        role="authenticated",
        access_token="test-token",
    )
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides.pop(get_current_user, None)


def test_chat_requires_authentication():
    response = client.post("/agent/chat", json={"message": "Hola"})

    assert response.status_code == 401


@pytest.mark.usefixtures("authenticated_user")
def test_chat_uses_authenticated_user_and_returns_conversation(
    monkeypatch,
):
    conversation_id = uuid4()
    received = {}

    def answer(message, user_id, access_token, conversation_id=None):
        received.update(
            message=message,
            user_id=user_id,
            access_token=access_token,
            conversation_id=conversation_id,
        )
        return "Revisa el sistema de refrigeración.", conversation_id or UUID(int=0)

    monkeypatch.setattr(chat_service, "answer", answer)
    response = client.post(
        "/agent/chat",
        json={
            "message": "¿Por qué se sobrecalienta?",
            "conversation_id": str(conversation_id),
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Revisa el sistema de refrigeración.",
        "conversation_id": str(conversation_id),
    }
    assert received == {
        "message": "¿Por qué se sobrecalienta?",
        "user_id": USER_ID,
        "access_token": "test-token",
        "conversation_id": conversation_id,
    }


@pytest.mark.usefixtures("authenticated_user")
def test_chat_returns_service_unavailable_when_ollama_is_unreachable(monkeypatch):
    monkeypatch.setattr(
        chat_service,
        "answer",
        Mock(side_effect=RequestError("Ollama server is unavailable")),
    )
    response = client.post("/agent/chat", json={"message": "Hola"})

    assert response.status_code == 503
    assert "Ollama no está disponible" in response.json()["detail"]


@pytest.mark.usefixtures("authenticated_user")
def test_history_endpoints_return_conversations_and_messages(monkeypatch):
    conversation_id = uuid4()
    timestamp = datetime(2026, 10, 18, tzinfo=timezone.utc).isoformat()
    summary = {
        "id": str(conversation_id),
        "title": "Consulta mecánica",
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    monkeypatch.setattr(
        chat_service,
        "list_conversations",
        Mock(return_value=[summary]),
    )
    monkeypatch.setattr(
        chat_service,
        "get_conversation",
        Mock(
            return_value={
                **summary,
                "messages": [
                    {
                        "id": str(uuid4()),
                        "role": "user",
                        "content": "¿Por qué se calienta?",
                        "created_at": timestamp,
                    }
                ],
                "next_offset": None,
            }
        ),
    )

    conversations_response = client.get("/agent/conversations")
    history_response = client.get(f"/agent/conversations/{conversation_id}")

    assert conversations_response.status_code == 200
    assert conversations_response.json()[0]["id"] == str(conversation_id)
    assert history_response.status_code == 200
    assert history_response.json()["messages"][0]["content"] == (
        "¿Por qué se calienta?"
    )


def test_graph_uses_messages_supplied_for_each_invocation(monkeypatch):
    fake_model = Mock()
    fake_model.invoke.return_value = AIMessage(content="Respuesta mecánica.")
    monkeypatch.setattr(agent, "ChatOllama", Mock(return_value=fake_model))
    graph = agent.build_graph()

    graph.invoke({"messages": [("user", "Primer mensaje")]})
    graph.invoke({"messages": [("user", "Otra conversación")]})

    calls = fake_model.invoke.call_args_list
    assert len(calls[0].args[0]) == 2
    assert len(calls[1].args[0]) == 2
    assert calls[0].args[0][0].content == agent.SYSTEM_PROMPT
    assert "no respondas la pregunta" in agent.SYSTEM_PROMPT
    assert "mi propósito es servir de guía" in agent.SYSTEM_PROMPT
