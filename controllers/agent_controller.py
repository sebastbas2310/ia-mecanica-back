from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List

from services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])
service = AgentService()


class CreateAgentRequest(BaseModel):
    user_id: str = Field(..., description="ID del usuario propietario")
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    model: str = "gpt-4o-mini"


class UpdateAgentRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    model: Optional[str] = None


class AskAgentRequest(BaseModel):
    user_id: str
    message: str = Field(..., min_length=1)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_agent(payload: CreateAgentRequest):
    try:
        return service.create_agent(
            user_id=payload.user_id,
            name=payload.name,
            description=payload.description,
            model=payload.model,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("")
def list_agents(user_id: str):
    try:
        return service.list_agents(user_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{agent_id}")
def get_agent(agent_id: str, user_id: str):
    try:
        return service.get_agent(agent_id, user_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/{agent_id}")
def update_agent(agent_id: str, user_id: str, payload: UpdateAgentRequest):
    try:
        return service.update_agent(
            agent_id=agent_id,
            user_id=user_id,
            name=payload.name,
            description=payload.description,
            model=payload.model,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{agent_id}")
def delete_agent(agent_id: str, user_id: str):
    try:
        return service.delete_agent(agent_id, user_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{agent_id}/ask")
def ask_agent(agent_id: str, payload: AskAgentRequest):
    try:
        return service.ask_agent(agent_id, payload.user_id, payload.message)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))