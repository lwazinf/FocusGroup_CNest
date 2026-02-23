"""
tests/test_core.py — Unit tests for FocusGroup room logic.

Covers (no live Ollama / Redis / ChromaDB required):
  - core.room      : RoomState management functions
  - core.persona_router : detect_command / detect_switch
  - core.nodes     : extract_thinking
  - core.summary   : build_markdown
"""
import pytest
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# core.room
# ─────────────────────────────────────────────────────────────────────────────

from core.room import (
    RoomState, PersonaContext,
    make_log_entry,
    add_persona_to_room,
    kick_persona_from_room,
    set_focus,
    clear_focus,
    append_log,
)


def _base_state() -> RoomState:
    return {
        "active_personas": ["1"],
        "focus_persona": "",
        "mode": "chat",
        "personas": {},
        "full_log": [],
    }


class TestRoomManagement:

    def test_add_persona_appends(self):
        s = add_persona_to_room(_base_state(), "2")
        assert s["active_personas"] == ["1", "2"]

    def test_add_persona_no_duplicate(self):
        s = add_persona_to_room(_base_state(), "1")
        assert s["active_personas"] == ["1"]

    def test_add_persona_immutable(self):
        original = _base_state()
        s = add_persona_to_room(original, "2")
        # original must not be mutated
        assert original["active_personas"] == ["1"]
        assert s["active_personas"] == ["1", "2"]

    def test_kick_persona_removes(self):
        s = _base_state()
        s = add_persona_to_room(s, "2")
        s = kick_persona_from_room(s, "1")
        assert s["active_personas"] == ["2"]

    def test_kick_persona_not_present_is_noop(self):
        s = kick_persona_from_room(_base_state(), "99")
        assert s["active_personas"] == ["1"]

    def test_kick_clears_focus_on_kicked_persona(self):
        s = _base_state()
        s = add_persona_to_room(s, "2")
        s = set_focus(s, "1")
        s = kick_persona_from_room(s, "1")
        assert s["focus_persona"] == ""

    def test_kick_preserves_focus_on_other_persona(self):
        s = _base_state()
        s = add_persona_to_room(s, "2")
        s = set_focus(s, "2")
        s = kick_persona_from_room(s, "1")
        assert s["focus_persona"] == "2"

    def test_set_focus(self):
        s = set_focus(_base_state(), "1")
        assert s["focus_persona"] == "1"

    def test_clear_focus(self):
        s = set_focus(_base_state(), "1")
        s = clear_focus(s)
        assert s["focus_persona"] == ""

    def test_append_log_grows(self):
        s = _base_state()
        entry = make_log_entry("user", "hello")
        s = append_log(s, entry)
        assert len(s["full_log"]) == 1
        s = append_log(s, make_log_entry("persona", "hi", "1", "Lena"))
        assert len(s["full_log"]) == 2

    def test_append_log_immutable(self):
        s = _base_state()
        entry = make_log_entry("user", "hello")
        s2 = append_log(s, entry)
        assert len(s["full_log"]) == 0
        assert len(s2["full_log"]) == 1


class TestMakeLogEntry:

    def test_user_entry(self):
        e = make_log_entry("user", "What do you think?")
        assert e["type"] == "user"
        assert e["content"] == "What do you think?"
        assert e["persona_key"] == ""
        assert e["thoughts"] == ""
        assert "timestamp" in e

    def test_persona_entry_with_thoughts(self):
        e = make_log_entry("persona", "I love it", "1", "Lena", "seems good")
        assert e["type"] == "persona"
        assert e["persona_name"] == "Lena"
        assert e["thoughts"] == "seems good"

    def test_system_entry(self):
        e = make_log_entry("system", "Lena joined.")
        assert e["type"] == "system"

    def test_timestamp_is_valid_iso(self):
        e = make_log_entry("user", "test")
        # Should parse without error
        datetime.fromisoformat(e["timestamp"])


# ─────────────────────────────────────────────────────────────────────────────
# core.persona_router
# ─────────────────────────────────────────────────────────────────────────────

from core.persona_router import detect_command, detect_switch


class TestDetectCommand:

    def test_exit(self):
        assert detect_command("!exit") == {"cmd": "exit"}
        assert detect_command("!EXIT") == {"cmd": "exit"}
        assert detect_command("  !exit  ") == {"cmd": "exit"}

    def test_reset(self):
        assert detect_command("!reset") == {"cmd": "reset"}

    def test_observe(self):
        assert detect_command("!observe") == {"cmd": "observe"}

    def test_unfocus_bare(self):
        assert detect_command("!focus") == {"cmd": "unfocus"}

    def test_add_known(self):
        r = detect_command("!add @lena")
        assert r["cmd"] == "add"
        assert r["persona_key"] == "1"
        assert r["persona_name"] == "lena"

    def test_add_known_uppercase(self):
        r = detect_command("!add @Lena")
        assert r["cmd"] == "add"
        assert r["persona_key"] == "1"

    def test_add_unknown(self):
        r = detect_command("!add @ghost")
        assert r["cmd"] == "add_unknown"
        assert r["persona_name"] == "ghost"

    def test_kick_known(self):
        r = detect_command("!kick @marcus")
        assert r["cmd"] == "kick"
        assert r["persona_key"] == "2"

    def test_kick_unknown(self):
        r = detect_command("!kick @nobody")
        assert r["cmd"] == "kick_unknown"

    def test_focus_known(self):
        r = detect_command("!focus @marcus")
        assert r["cmd"] == "focus"
        assert r["persona_key"] == "2"

    def test_focus_unknown(self):
        r = detect_command("!focus @phantom")
        assert r["cmd"] == "focus_unknown"

    def test_normal_message_returns_none(self):
        assert detect_command("What do you think of the PS5?") is None
        assert detect_command("hello") is None
        assert detect_command("") is None

    def test_partial_commands_return_none(self):
        assert detect_command("!ad @lena") is None
        assert detect_command("add @lena") is None
        assert detect_command("!add lena") is None   # missing @


class TestDetectSwitch:

    def test_switch_to_lena(self):
        assert detect_switch("@lena") == "1"

    def test_switch_to_marcus(self):
        assert detect_switch("@marcus") == "2"

    def test_switch_case_insensitive(self):
        assert detect_switch("@LENA") == "1"
        assert detect_switch("@Marcus") == "2"

    def test_no_switch_on_normal_text(self):
        assert detect_switch("hello @lena how are you") is None
        assert detect_switch("random") is None


# ─────────────────────────────────────────────────────────────────────────────
# core.nodes — extract_thinking
# ─────────────────────────────────────────────────────────────────────────────

from core.nodes import extract_thinking


class TestExtractThinking:

    def test_extracts_think_block(self):
        raw = "<think>\nI need to think about this.\n</think>\n\nActual response."
        thoughts, response = extract_thinking(raw)
        assert thoughts == "I need to think about this."
        assert response == "Actual response."

    def test_no_think_block(self):
        raw = "Just a plain response."
        thoughts, response = extract_thinking(raw)
        assert thoughts == ""
        assert response == "Just a plain response."

    def test_think_block_inline(self):
        thoughts, response = extract_thinking("<think>quick</think>Answer.")
        assert thoughts == "quick"
        assert response == "Answer."

    def test_think_block_with_multiline_thoughts(self):
        raw = "<think>\nLine one.\nLine two.\n</think>\nFinal answer."
        thoughts, response = extract_thinking(raw)
        assert "Line one." in thoughts
        assert "Line two." in thoughts
        assert response == "Final answer."

    def test_response_stripped(self):
        raw = "<think>t</think>   spaced response   "
        _, response = extract_thinking(raw)
        assert response == "spaced response"

    def test_thoughts_stripped(self):
        raw = "<think>  padded thoughts  </think>response"
        thoughts, _ = extract_thinking(raw)
        assert thoughts == "padded thoughts"

    def test_empty_think_block(self):
        thoughts, response = extract_thinking("<think></think>response")
        assert thoughts == ""
        assert response == "response"

    def test_think_block_at_end_leaves_empty_response(self):
        thoughts, response = extract_thinking("<think>only thoughts</think>")
        assert thoughts == "only thoughts"
        assert response == ""


# ─────────────────────────────────────────────────────────────────────────────
# core.summary — build_markdown (no LLM call)
# ─────────────────────────────────────────────────────────────────────────────

from core.summary import build_markdown


def _sample_log():
    return [
        {
            "timestamp": "2026-02-23T10:00:00",
            "type": "system",
            "persona_key": "",
            "persona_name": "",
            "thoughts": "",
            "content": "Lena joined the room.",
        },
        {
            "timestamp": "2026-02-23T10:01:00",
            "type": "user",
            "persona_key": "",
            "persona_name": "",
            "thoughts": "",
            "content": "What do you think of the PS5?",
        },
        {
            "timestamp": "2026-02-23T10:02:00",
            "type": "persona",
            "persona_key": "1",
            "persona_name": "Lena",
            "thoughts": "Specs are solid.",
            "content": "I think the PS5 has great performance.",
        },
        {
            "timestamp": "2026-02-23T10:03:00",
            "type": "persona",
            "persona_key": "2",
            "persona_name": "Marcus",
            "thoughts": "",
            "content": "It feels refined.",
        },
    ]


class TestBuildMarkdown:

    def test_has_title(self):
        md = build_markdown("Summary text.", _sample_log())
        assert "# Focus Group Session Summary" in md

    def test_has_executive_summary_section(self):
        md = build_markdown("Summary text.", _sample_log())
        assert "## Executive Summary" in md
        assert "Summary text." in md

    def test_has_chat_log_section(self):
        md = build_markdown("Summary text.", _sample_log())
        assert "## Full Chat Log" in md

    def test_user_message_formatted(self):
        md = build_markdown("s", _sample_log())
        # Format includes timestamp: **[HH:MM:SS] Moderator:**
        assert "Moderator:**" in md
        assert "What do you think of the PS5?" in md

    def test_persona_message_formatted(self):
        md = build_markdown("s", _sample_log())
        assert "**[10:02:00] Lena:**" in md
        assert "I think the PS5 has great performance." in md

    def test_thoughts_shown_when_present(self):
        md = build_markdown("s", _sample_log())
        assert "Specs are solid." in md
        assert "\U0001f4ad" in md  # 💭

    def test_no_thoughts_block_when_empty(self):
        md = build_markdown("s", _sample_log())
        # Marcus has no thoughts; check his block has no thought prefix
        marcus_section = md.split("**[10:03:00] Marcus:**")[1].split("\n\n")[0]
        assert "\U0001f4ad" not in marcus_section

    def test_system_entry_formatted(self):
        md = build_markdown("s", _sample_log())
        assert "Lena joined the room." in md
        assert "⚙" in md

    def test_empty_log_produces_valid_markdown(self):
        md = build_markdown("Empty session.", [])
        assert "# Focus Group Session Summary" in md
        assert "Empty session." in md

    def test_timestamp_formatted_as_hhmmss(self):
        md = build_markdown("s", _sample_log())
        # Chat log entries should use HH:MM:SS, not full ISO timestamp
        assert "[10:01:00]" in md
        assert "2026-02-23T10:01:00" not in md  # raw ISO should not appear
