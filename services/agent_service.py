from typing import Any, Dict, List, Optional
from supabase_client import supabase


class AgentService:
    def __init__(self):
        self.table = supabase.table("agents")

    def create_agent(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        payload = {
            "user_id": user_id,
            "name": name,
            "description": description,
            "model": model,
            "status": "active",
        }
        result = self.table.insert(payload).execute()
        if not result.data:
            raise ValueError("No se pudo crear el agente")
        return result.data[0]

    def list_agents(self, user_id: str) -> List[Dict[str, Any]]:
        result = self.table.select("*").eq("user_id", user_id).execute()
        return result.data

    def get_agent(self, agent_id: str, user_id: str) -> Dict[str, Any]:
        result = (
            self.table
            .select("*")
            .eq("id", agent_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise ValueError("Agente no encontrado")
        return result.data[0]

    def update_agent(
        self,
        agent_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        payload = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if model is not None:
            payload["model"] = model

        result = (
            self.table
            .update(payload)
            .eq("id", agent_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not result.data:
            raise ValueError("No se pudo actualizar el agente")
        return result.data[0]

    def delete_agent(self, agent_id: str, user_id: str) -> Dict[str, Any]:
        result = (
            self.table
            .delete()
            .eq("id", agent_id)
            .eq("user_id", user_id)
            .execute()
        )
        return {"deleted": True, "agent_id": agent_id}

    def ask_agent(self, agent_id: str, user_id: str, message: str) -> Dict[str, Any]:
        agent = self.get_agent(agent_id, user_id)

        # Aquí podrías llamar a tu chat_service o a una IA
        # response = ChatService().send_message(agent["model"], message)
        return {
            "agent_id": agent_id,
            "user_id": user_id,
            "message": message,
            "response": f"Respuesta simulada para el agente {agent['name']}",
        }