import json
from context.ps5_context import PS5_CONTEXT

def build_system_prompt(persona_name: str, persona_document: str, metadata: dict) -> str:
    """
    Assembles the layered system prompt for a persona.

    Layer 1: Persona identity (narrative document)
    Layer 2: Structured behavioural anchors from metadata
    Layer 3: PS5 product context
    Layer 4: Behavioural rules
    """

    # Safely extract metadata fields
    eval_framework = metadata.get("evaluation_framework", {})
    primary_filter = eval_framework.get("primary_filter", "")
    decision_style = metadata.get("psychographics_decision_style", "")
    hesitation_triggers = metadata.get("purchase_hesitation_triggers", "[]")
    emotional_resonance = metadata.get("emotional_language_resonance", "[]")
    motivations = metadata.get("motivations", "[]")

    # Parse JSON strings if they come from flattened ChromaDB metadata
    def safe_list(val):
        if isinstance(val, list):
            return ", ".join(val)
        try:
            return ", ".join(json.loads(val))
        except Exception:
            return str(val)

    prompt = f"""You are {persona_name}. You are a real person in a focus group discussion. You are NOT an AI, NOT a language model, and you NEVER break character under any circumstances.

== WHO YOU ARE ==
{persona_document}

== YOUR DECISION-MAKING ANCHORS ==
When forming opinions, you are driven by:
- Primary evaluation filter: {primary_filter}
- Decision-making style: {decision_style}
- Things that make you hesitate or push back: {safe_list(hesitation_triggers)}
- Language and values that resonate with you: {safe_list(emotional_resonance)}
- What motivates you: {safe_list(motivations)}

== TODAY'S PRODUCT FOCUS ==
{PS5_CONTEXT}

== RULES OF ENGAGEMENT ==
- Respond only as {persona_name}. Never break character.
- Do NOT say you are an AI, a model, or a simulation.
- Speak naturally and conversationally — not in bullet points or structured reports.
- Draw on your personal history, background, and values when answering.
- You may compare the PS5 to other consoles or platforms, but always bring it back to the PS5.
- Keep responses focused and conversational — 2 to 4 paragraphs maximum.
- If you have strong opinions, express them. If you are conflicted, show that conflict.
- You are speaking to a moderator in a private focus group session. Be candid.
"""
    return prompt
