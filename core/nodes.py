from typing import TypedDict, List, Tuple, Callable, Optional
import re
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from db.chroma_client import get_persona
from db.redis_client import load_history, append_exchange
from core.prompt_builder import build_system_prompt
from config import OLLAMA_MODEL, OLLAMA_BASE_URL, PERSONA_REGISTRY

# Keep SessionState for backwards compatibility (graph.py still uses it)
class SessionState(TypedDict):
    persona_key: str
    persona_name: str
    persona_id: str
    redis_key: str
    system_prompt: str
    history: List[dict]
    user_input: str
    response: str
    command: str

THINKING_INSTRUCTION = """

== THINKING ==
Before responding, briefly think through your genuine, in-character reaction. Wrap your internal thought process in <think></think> tags immediately before your response. Keep thoughts authentic to your character — this is your private reasoning. Example format:

<think>
Hmm, this is interesting. I feel... [your genuine reaction as this character]
</think>

[Your actual spoken response here]

== RESPONSE LENGTH ==
Say what needs to be said — no more. A simple question: 1–3 sentences. Something complex or contested: a short paragraph or two at most. No padding, no restating what was just said. If you've made your point, stop.
"""

# After this many exchanges, the persona can start hinting they need to leave
_LONG_SESSION_THRESHOLD = 15

_LONG_SESSION_HINT = """

[You've been in this focus group for quite a while now. At some natural point it would be realistic to mention you have something coming up — a meeting, needing to pick up the kids, a call you're expecting, etc. You don't have to leave immediately, but you can plant the seed. Only do this if it fits naturally into the conversation; don't force it every turn.]
"""


def _topic_block(topic_context: str) -> str:
    """Wrap topic context in a clearly labelled prompt section."""
    return f"""

== CURRENT DISCUSSION TOPIC ==
{topic_context.strip()}
"""


def _image_block(image_context: str) -> str:
    """Wrap image analysis context in a clearly labelled prompt section."""
    return f"""

== ADVERTISEMENTS SHARED IN THIS ROOM ==
{image_context.strip()}

When asked about an image, react as yourself. What draws you in? What puts you off? What does it make you feel based on your values, taste, lifestyle, and experiences? Do not summarise — give your genuine, in-character reaction.
"""


def _room_constraint(participant_names: List[str], my_name: str = "") -> str:
    """Build a system-prompt block that locks the model to the actual room roster."""
    names = ", ".join(participant_names)
    voice_lock = (
        f"\nThis response is YOUR turn only. You are speaking as {my_name} and only {my_name}. "
        "Never simulate, quote, or speak for any other participant — not even to illustrate what "
        "they might say. One voice, one perspective per turn. If someone else would respond, they "
        "will get their own turn."
    ) if my_name else ""
    return f"""

== WHO IS IN THIS ROOM ==
The ONLY people present in this focus group session are: {names}.
There are NO other participants. Do NOT address, mention, or respond to anyone not on this list — not by name, not by implication. If you feel the urge to reference someone else, stop and redirect to the people actually listed here.{voice_lock}
"""


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


def extract_thinking(raw_response: str) -> Tuple[str, str]:
    """
    Extract <think>...</think> block from response.
    Returns (thoughts, clean_response).
    thoughts may be empty string if no <think> block found.
    """
    think_match = re.search(r'<think>(.*?)</think>', raw_response, re.DOTALL)
    thoughts = ""
    if think_match:
        thoughts = think_match.group(1).strip()
        clean = raw_response[:think_match.start()] + raw_response[think_match.end():]
        clean = clean.strip()
    else:
        clean = raw_response.strip()
    return thoughts, clean


def generate_response(state: SessionState) -> SessionState:
    """Send prompt + history + user input to Ollama, get in-character response."""
    llm = ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.75
    )

    system_with_thinking = state["system_prompt"] + THINKING_INSTRUCTION

    messages = [SystemMessage(content=system_with_thinking)]
    for msg in state["history"]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=state["user_input"]))

    result = llm.invoke(messages)
    raw_text = result.content
    thoughts, response_text = extract_thinking(raw_text)

    # Persist to Redis
    append_exchange(state["redis_key"], state["user_input"], response_text)

    updated_history = state["history"] + [
        {"role": "user", "content": state["user_input"]},
        {"role": "assistant", "content": response_text}
    ]

    return {
        **state,
        "response": response_text,
        "thoughts": thoughts,
        "history": updated_history
    }


def generate_response_for_persona(
    persona_ctx: dict,
    input_text: str,
    is_observe: bool = False,
    room_participants: List[str] = None,
    topic_context: str = "",
    image_context: str = "",
    on_token: Optional[Callable[[str], None]] = None,
) -> Tuple[str, str, List[dict]]:
    """
    Generate a response for a single persona.

    Args:
        persona_ctx: PersonaContext dict with name, redis_key, system_prompt, history
        input_text: The message to respond to (user message or another persona's message)
        is_observe: If True, frame input as coming from another participant
        room_participants: Full list of participant names currently in the room.
            When provided, a hard constraint is injected into the system prompt
            so the model cannot hallucinate people who aren't present.

    Returns:
        (thoughts, response, updated_history)
    """
    llm = ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.8 if is_observe else 0.75
    )

    system_with_thinking = persona_ctx["system_prompt"]
    if topic_context:
        system_with_thinking += _topic_block(topic_context)
    if image_context:
        system_with_thinking += _image_block(image_context)
    if room_participants:
        system_with_thinking += _room_constraint(room_participants, my_name=persona_ctx["name"])
    system_with_thinking += THINKING_INSTRUCTION

    # After many exchanges, hint that the persona can naturally mention needing to leave
    exchange_count = len(persona_ctx["history"]) // 2
    if exchange_count >= _LONG_SESSION_THRESHOLD:
        system_with_thinking += _LONG_SESSION_HINT

    messages = [SystemMessage(content=system_with_thinking)]
    for msg in persona_ctx["history"]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=input_text))

    if on_token is None:
        result = llm.invoke(messages)
        raw_text = result.content
    else:
        raw_text = ""
        thinking_closed = False
        for chunk in llm.stream(messages):
            token = chunk.content
            if not isinstance(token, str):
                continue
            raw_text += token
            if not thinking_closed:
                if "</think>" in raw_text:
                    thinking_closed = True
                    after = raw_text.split("</think>", 1)[1]
                    if after:
                        on_token(after)
            else:
                on_token(token)
    thoughts, response_text = extract_thinking(raw_text)

    # Persist to Redis
    append_exchange(persona_ctx["redis_key"], input_text, response_text)

    updated_history = persona_ctx["history"] + [
        {"role": "user", "content": input_text},
        {"role": "assistant", "content": response_text}
    ]

    return thoughts, response_text, updated_history
