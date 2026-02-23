from typing import TypedDict, List
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from db.chroma_client import get_persona
from db.redis_client import load_history, append_exchange
from core.prompt_builder import build_system_prompt
from config import OLLAMA_MODEL, OLLAMA_BASE_URL, PERSONA_REGISTRY

class SessionState(TypedDict):
    persona_key: str           # '1' or '2'
    persona_name: str
    persona_id: str
    redis_key: str
    system_prompt: str
    history: List[dict]
    user_input: str
    response: str
    command: str               # 'reset', 'exit', 'switch', or ''

def assemble_context(state: SessionState) -> SessionState:
    """Load persona from ChromaDB, build system prompt, load Redis history."""
    persona_key = state["persona_key"]
    reg = PERSONA_REGISTRY[persona_key]

    persona_data = get_persona(reg["id"])
    system_prompt = build_system_prompt(
        persona_name=reg["name"],
        persona_document=persona_data["document"],
        metadata=persona_data["metadata"]
    )
    history = load_history(reg["redis_key"])

    return {
        **state,
        "persona_name": reg["name"],
        "persona_id": reg["id"],
        "redis_key": reg["redis_key"],
        "system_prompt": system_prompt,
        "history": history,
        "command": ""
    }

def generate_response(state: SessionState) -> SessionState:
    """Send prompt + history + user input to Ollama, get in-character response."""
    llm = ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.75
    )

    messages = [SystemMessage(content=state["system_prompt"])]
    for msg in state["history"]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=state["user_input"]))

    result = llm.invoke(messages)
    response_text = result.content

    # Persist to Redis
    append_exchange(state["redis_key"], state["user_input"], response_text)

    # Update in-memory history
    updated_history = state["history"] + [
        {"role": "user", "content": state["user_input"]},
        {"role": "assistant", "content": response_text}
    ]

    return {
        **state,
        "response": response_text,
        "history": updated_history
    }
