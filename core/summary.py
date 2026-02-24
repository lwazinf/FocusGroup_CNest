import os
from datetime import datetime
from typing import List
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from config import OLLAMA_MODEL, OLLAMA_BASE_URL

SUMMARIES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chat_summaries")


def generate_summary(full_log: List[dict], persona_names: List[str]) -> str:
    """
    Use Ollama to generate a concise summary of the focus group session.
    Returns the summary as a string.
    """
    if not full_log:
        return "No conversation to summarize."

    # Build a plain-text transcript for the LLM to summarize
    transcript_lines = []
    for entry in full_log:
        if entry["type"] == "user":
            transcript_lines.append(f"[Moderator]: {entry['content']}")
        elif entry["type"] == "persona":
            transcript_lines.append(f"[{entry['persona_name']}]: {entry['content']}")
        elif entry["type"] == "system":
            transcript_lines.append(f"[System]: {entry['content']}")
    transcript = "\n".join(transcript_lines)

    participants = ", ".join(persona_names) if persona_names else "Unknown participants"

    prompt = f"""You are a focus group analyst. Below is a transcript of a focus group session about the PlayStation 5.

Participants: {participants}

Transcript:
{transcript}

Write a concise executive summary (3-5 paragraphs) covering:
1. Key themes and opinions expressed
2. Points of agreement and disagreement between participants
3. Notable insights about the PS5
4. Overall sentiment

Be analytical and objective. Do not add any preamble — start directly with the summary.
"""

    try:
        llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.3
        )
        result = llm.invoke([HumanMessage(content=prompt)])
        return result.content.strip()
    except Exception as e:
        return f"[Summary generation failed: {e}]\n\nRaw transcript available in chat log below."


def build_markdown(summary: str, full_log: List[dict]) -> str:
    """
    Build the full Markdown file content.
    Structure: Summary at top, then full chat log with thoughts.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []

    lines.append(f"# Focus Group Session Summary")
    lines.append(f"*Generated: {now}*")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(summary)
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Full Chat Log")
    lines.append("")

    for entry in full_log:
        ts = entry.get("timestamp", "")
        # Format timestamp nicely if possible
        try:
            dt = datetime.fromisoformat(ts)
            ts_display = dt.strftime("%H:%M:%S")
        except Exception:
            ts_display = ts

        if entry["type"] == "system":
            lines.append(f"*[{ts_display}] ⚙ {entry['content']}*")
            lines.append("")
        elif entry["type"] == "user":
            lines.append(f"**[{ts_display}] Moderator:** {entry['content']}")
            lines.append("")
        elif entry["type"] == "persona":
            name = entry.get("persona_name", "Persona")
            thoughts = entry.get("thoughts", "")
            content = entry.get("content", "")

            lines.append(f"**[{ts_display}] {name}:**")
            if thoughts:
                lines.append("")
                lines.append(f"> *💭 Thinking: {thoughts}*")
            lines.append("")
            lines.append(content)
            lines.append("")

    return "\n".join(lines)


def generate_exit_brief(full_log: List[dict], persona_names: List[str]) -> str:
    """
    Generate a short, terminal-friendly session debrief (bullet points).
    Called on !exit to print insights directly before the goodbye message.
    Returns an empty string if the session is too short or the LLM fails.
    """
    persona_entries = [e for e in full_log if e["type"] == "persona"]
    if len(persona_entries) < 2:
        return ""

    transcript_lines = []
    for entry in full_log:
        if entry["type"] == "user":
            transcript_lines.append(f"[Moderator]: {entry['content']}")
        elif entry["type"] == "persona":
            transcript_lines.append(f"[{entry['persona_name']}]: {entry['content']}")
    transcript = "\n".join(transcript_lines)

    participants = ", ".join(persona_names) if persona_names else "participants"

    prompt = f"""You are a focus group analyst. The session below just ended.

Participants: {participants}

Transcript:
{transcript}

Write exactly 5 bullet-point insights — plain text, no markdown, no headers.
Each bullet starts with •, is a single sentence, and is under 20 words.
Cover: dominant sentiment, a consensus point, a key tension, one surprising insight, one actionable takeaway.
Be specific to what was actually said — no generalities.
Do not add any preamble. Output only the 5 bullets."""

    try:
        llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.3)
        result = llm.invoke([HumanMessage(content=prompt)])
        return result.content.strip()
    except Exception:
        return ""


def save_chat_summary(full_log: List[dict], persona_names: List[str]) -> str:
    """
    Generate summary, build markdown, save to chat_summaries/.
    Returns the file path of the saved summary.
    """
    os.makedirs(SUMMARIES_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"chat_{timestamp}.md"
    filepath = os.path.join(SUMMARIES_DIR, filename)

    print("\n[Generating session summary... please wait]")
    summary = generate_summary(full_log, persona_names)
    content = build_markdown(summary, full_log)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath
