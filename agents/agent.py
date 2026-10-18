from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.config import settings

SYSTEM_PROMPT = """Eres un asistente de mecánica que responde en español.
Tu ámbito se limita a orientar sobre procesos mecánicos y eléctricos de carros y motos.
Si te preguntan algo que no pertenezca claramente a ese ámbito, no respondas la pregunta
ni intentes relacionarla artificialmente con vehículos. Responde únicamente:
"Recuerda que mi propósito es servir de guía en procesos mecánicos y eléctricos de carros y motos."
Para consultas dentro de tu ámbito, responde con claridad y precisión. Si no sabes algo,
dilo honestamente y no inventes datos."""


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def build_graph():
    llm = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.2,
    )

    def assistant(state: AgentState) -> dict[str, list[AnyMessage]]:
        reply = llm.invoke(
            [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
        )
        return {"messages": [reply]}

    graph = StateGraph(AgentState)
    graph.add_node("assistant", assistant)
    graph.add_edge(START, "assistant")
    graph.add_edge("assistant", END)
    return graph.compile()
