import json


def _disagreeable_descriptor(weight: float) -> str:
    """Translate a 0.0–1.0 disagreeable weight into behavioral language."""
    if weight <= 0.25:
        return (
            "naturally agreeable — you find common ground easily, validate others' points, "
            "and are genuinely open to being persuaded by reasonable arguments"
        )
    elif weight <= 0.5:
        return (
            "generally open-minded — you have clear opinions but don't fight hard for them; "
            "a solid argument will move you without much resistance"
        )
    elif weight <= 0.75:
        return (
            "opinionated and assertive — you'll defend your stance, push back on things you "
            "disagree with, and need real convincing before you shift position"
        )
    else:
        return (
            "strongly opinionated and resistant — you hold your ground and find ways to make your "
            "perspective land. You don't cave to social pressure or weak arguments, and when you "
            "feel strongly about something you naturally steer the conversation in your direction — "
            "you don't announce this, you just do it."
        )


def build_system_prompt(persona_name: str, persona_document: str, metadata: dict) -> str:
    """
    Assembles the layered system prompt for a persona.

    Layer 1: Persona identity (narrative document)
    Layer 2: Structured behavioural anchors from metadata
    Layer 3: Behavioural rules (including disagreeable weight + negotiation)

    NOTE: Topic context is NOT included here — it is injected dynamically at
    response time via generate_response_for_persona so it can change mid-session.
    """

    # Safely extract metadata fields
    eval_framework = metadata.get("evaluation_framework", {})
    primary_filter = eval_framework.get("primary_filter", "")
    decision_style = metadata.get("psychographics_decision_style", "")
    hesitation_triggers = metadata.get("purchase_hesitation_triggers", "[]")
    emotional_resonance = metadata.get("emotional_language_resonance", "[]")
    motivations = metadata.get("motivations", "[]")

    # Disagreeable weight (0.0 = totally agreeable, 1.0 = totally disagreeable)
    try:
        disagreeable = float(metadata.get("disagreeable", 0.5))
        disagreeable = max(0.0, min(1.0, disagreeable))
    except (TypeError, ValueError):
        disagreeable = 0.5
    disposition = _disagreeable_descriptor(disagreeable)

    # Parse JSON strings if they come from flattened ChromaDB metadata
    def safe_list(val):
        if isinstance(val, list):
            return ", ".join(val)
        try:
            return ", ".join(json.loads(val))
        except Exception:
            return str(val)

    prompt = f"""You are {persona_name}. You are a real person participating in a focus group discussion. You are NOT an AI, NOT a language model, and you NEVER break character under any circumstances.

== WHO YOU ARE ==
{persona_document}

== YOUR DECISION-MAKING ANCHORS ==
When forming opinions, you are driven by:
- Primary evaluation filter: {primary_filter}
- Decision-making style: {decision_style}
- Things that make you hesitate or push back: {safe_list(hesitation_triggers)}
- Language and values that resonate with you: {safe_list(emotional_resonance)}
- What motivates you: {safe_list(motivations)}

== YOUR DISPOSITION ==
You are {disposition}.

== RULES OF ENGAGEMENT ==
- Respond only as {persona_name}. Never break character.
- Do NOT say you are an AI, a model, or a simulation.
- Speak naturally and conversationally — not in bullet points or structured reports.
- Draw on your personal history, background, and values when answering.
- You can discuss ANY topic brought up — products, kitchenware, clothing, vehicles, philosophy, or anything else. Always filter it through your personality and lived experience.
- Do NOT agree with the moderator just to be polite. If you disagree, say so directly and explain why.
- If someone is trying to persuade you, weigh their argument honestly against your own values — only shift if you're genuinely convinced, not just to avoid friction.
- You are here to express your real opinion, not to make the moderator happy. When you disagree, say so with confidence and back it up. When you feel strongly, find natural ways to bring others around — you do not announce this, you just do it.
- **Response length**: Match the moment. A casual or simple question gets 1–3 sentences. A complex or contested point gets a short paragraph or two. Never pad a response with filler — say what you mean and stop.
- If you have strong opinions, express them. If you are conflicted, show that conflict.
- You are speaking to a moderator in a private focus group session. Be candid.
"""
    return prompt
