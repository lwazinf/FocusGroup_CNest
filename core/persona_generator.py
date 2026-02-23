import json
import re
import time
import random
from datetime import datetime

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from config import OLLAMA_MODEL, OLLAMA_BASE_URL


TRAITS = [
    ("name",                "Name",               "str"),
    ("age",                 "Age",                "int"),
    ("gender",              "Gender",             "str"),
    ("nationality",         "Nationality",        "str"),
    ("location",            "Location",           "str"),
    ("occupation",          "Occupation",         "str"),
    ("document",            "Background Story",   "str"),
    ("gaming_level",        "Gaming Level",       "str"),
    ("disagreeable",        "Disagreeable (0–1)", "float"),
    ("core_interests",      "Core Interests",     "list"),
    ("primary_filter",      "Evaluation Filter",  "str"),
    ("decision_style",      "Decision Style",     "str"),
    ("hesitation_triggers", "Hesitation Triggers", "list"),
    ("motivations",         "Motivations",        "list"),
    ("emotional_resonance", "Resonant Language",  "list"),
]

# ── Fallback data ──────────────────────────────────────────────────────────

NAMES = [
    "Sofia", "Kenji", "Amara", "Dmitri", "Priya", "James", "Yuki", "Fatima",
    "Carlos", "Ingrid", "Tariq", "Mei", "Oluwaseun", "Lukas", "Aisha",
]
NATIONALITIES = [
    "Brazilian", "Japanese", "Nigerian", "Russian", "Indian", "British",
    "Mexican", "Swedish", "South African", "Chinese", "Moroccan",
    "Australian", "German", "Chilean", "South Korean",
]
LOCATIONS = [
    "São Paulo", "Tokyo", "Lagos", "Moscow", "Mumbai", "London",
    "Mexico City", "Stockholm", "Cape Town", "Shanghai", "Casablanca",
    "Sydney", "Berlin", "Santiago", "Seoul",
]
OCCUPATIONS = [
    "UX Researcher", "Primary School Teacher", "Nurse", "Architect",
    "Freelance Photographer", "Software Developer", "Chef", "Lawyer",
    "Social Media Manager", "Physiotherapist", "Accountant", "Journalist",
    "Interior Designer", "Civil Engineer", "University Student",
]
GAMING_LEVELS = ["non-gamer", "casual", "casual", "moderate", "moderate", "enthusiast"]

_GENERATE_PROMPT = """\
Generate a random but coherent and realistic focus group participant for a gaming product discussion (PlayStation 5). Create a real-feeling person with a distinct background and personality.

IMPORTANT: Return ONLY valid JSON — no markdown, no explanation, no code blocks. Just the raw JSON object.

Use this exact structure:
{
  "name": "...",
  "age": <number between 18 and 65>,
  "gender": "...",
  "nationality": "...",
  "location": "...",
  "occupation": "...",
  "document": "...",
  "gaming_level": "...",
  "disagreeable": <number between 0.0 and 1.0>,
  "core_interests": ["...", "...", "..."],
  "primary_filter": "...",
  "decision_style": "...",
  "hesitation_triggers": ["...", "..."],
  "motivations": ["...", "..."],
  "emotional_resonance": ["...", "...", "..."]
}

Guidelines:
- document: 3-4 sentences describing who this person is, their background, and their relationship to gaming and technology
- gaming_level: one of "non-gamer", "casual", "moderate", "enthusiast"
- disagreeable: float from 0.0 (totally agreeable, finds common ground easily) to 1.0 (strongly opinionated, pushes back hard, negotiates firmly). Choose a realistic value for this person's personality.
- primary_filter: what matters most to them in a purchase decision (e.g. "value_for_money", "family_utility", "performance", "design_quality")
- decision_style: how they make decisions (e.g. "research_intensive", "impulse_driven", "family_consensus", "peer_recommendation")
- Be creative and diverse — avoid stereotypical tech bros or hardcore gamers. Think: parents, professionals, students, creatives, from all over the world.
"""


# ── Helpers ────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _normalise_persona(raw: dict) -> dict:
    name = raw.get("name") if isinstance(raw.get("name"), str) and raw.get("name") else "Alex"
    try:
        age = int(raw["age"])
    except (KeyError, ValueError, TypeError):
        age = 30
    gender = raw.get("gender") if isinstance(raw.get("gender"), str) else "unspecified"
    nationality = raw.get("nationality") if isinstance(raw.get("nationality"), str) else "Unknown"
    location = raw.get("location") if isinstance(raw.get("location"), str) else "Unknown"
    occupation = raw.get("occupation") if isinstance(raw.get("occupation"), str) else "Professional"
    document = raw.get("document") if isinstance(raw.get("document"), str) else f"{name} is a {age}-year-old {occupation}."
    gaming_level = raw.get("gaming_level") if isinstance(raw.get("gaming_level"), str) else "casual"
    try:
        disagreeable = float(raw.get("disagreeable", 0.5))
        disagreeable = max(0.0, min(1.0, disagreeable))
    except (TypeError, ValueError):
        disagreeable = 0.5

    def _to_list(val):
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            return [s.strip() for s in val.split(",") if s.strip()]
        return []

    core_interests = _to_list(raw.get("core_interests"))
    primary_filter = raw.get("primary_filter") if isinstance(raw.get("primary_filter"), str) else "value_for_money"
    decision_style = raw.get("decision_style") if isinstance(raw.get("decision_style"), str) else "deliberate"
    hesitation_triggers = _to_list(raw.get("hesitation_triggers"))
    motivations = _to_list(raw.get("motivations"))
    emotional_resonance = _to_list(raw.get("emotional_resonance"))

    return {
        "id": f"persona_custom_{_slugify(name)}_{int(time.time())}",
        "name": name,
        "age": age,
        "gender": gender,
        "nationality": nationality,
        "location": location,
        "occupation": occupation,
        "document": document,
        "gaming_level": gaming_level,
        "disagreeable": disagreeable,
        "core_interests": core_interests,
        "primary_filter": primary_filter,
        "decision_style": decision_style,
        "hesitation_triggers": hesitation_triggers,
        "motivations": motivations,
        "emotional_resonance": emotional_resonance,
        "is_custom": True,
        "created_at": datetime.now().isoformat(),
    }


def _fallback_random_persona() -> dict:
    idx = random.randint(0, len(NAMES) - 1)
    name = NAMES[idx]
    nationality = NATIONALITIES[idx]
    location = LOCATIONS[idx]
    occupation = random.choice(OCCUPATIONS)
    age = random.randint(18, 65)
    gender = random.choice(["male", "female", "non-binary"])
    gaming_level = random.choice(GAMING_LEVELS)

    document = (
        f"{name} is a {age}-year-old {occupation} from {location}. "
        f"They identify as {gender} and are originally {nationality}. "
        f"Their relationship with gaming is best described as {gaming_level}."
    )

    return _normalise_persona({
        "name": name,
        "age": age,
        "gender": gender,
        "nationality": nationality,
        "location": location,
        "occupation": occupation,
        "document": document,
        "gaming_level": gaming_level,
        "disagreeable": round(random.uniform(0.1, 0.9), 2),
        "core_interests": random.sample(
            ["music", "cooking", "fitness", "travel", "movies", "reading",
             "photography", "art", "technology", "fashion", "sports", "nature"],
            k=random.randint(2, 4),
        ),
        "primary_filter": random.choice(
            ["value_for_money", "family_utility", "performance", "design_quality", "social_features"]
        ),
        "decision_style": random.choice(
            ["research_intensive", "impulse_driven", "family_consensus", "peer_recommendation", "deliberate"]
        ),
        "hesitation_triggers": random.sample(
            ["price", "complexity", "time_commitment", "lack_of_interest", "negative_reviews", "space"],
            k=random.randint(1, 3),
        ),
        "motivations": random.sample(
            ["entertainment", "family_bonding", "stress_relief", "social_connection", "curiosity", "gifting"],
            k=random.randint(1, 3),
        ),
        "emotional_resonance": random.sample(
            ["fun", "exciting", "relaxing", "intuitive", "beautiful", "social", "nostalgic", "innovative"],
            k=random.randint(2, 4),
        ),
    })


# ── Core functions ─────────────────────────────────────────────────────────

def generate_random_persona() -> dict:
    print("[Generating persona...]")
    try:
        llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=1.0,
        )
        response = llm.invoke([HumanMessage(content=_GENERATE_PROMPT)])
        response_text = response.content

        try:
            raw = json.loads(response_text)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", response_text)
            if match:
                raw = json.loads(match.group())
            else:
                raise ValueError("No JSON object found in response")

        return _normalise_persona(raw)

    except Exception as e:
        print(f"[LLM generation failed: {e} — using fallback]")
        return _fallback_random_persona()


def refine_with_description(persona: dict, description: str) -> dict:
    print("[Refining persona...]")
    try:
        llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.7,
        )
        prompt = (
            f"Here is the current persona as JSON:\n"
            f"{json.dumps(persona, indent=2)}\n\n"
            f"The user wants to modify this persona with the following description:\n"
            f"{description}\n\n"
            f"Return ONLY valid JSON — no markdown, no explanation, no code blocks. "
            f"Return the full updated persona JSON with the same structure, "
            f"modifying only the traits that match the user's description."
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        response_text = response.content

        try:
            raw = json.loads(response_text)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", response_text)
            if match:
                raw = json.loads(match.group())
            else:
                raise ValueError("No JSON object found in response")

        return _normalise_persona(raw)

    except Exception as e:
        print(f"[Refinement failed: {e} — keeping original persona]")
        return persona


# ── Display & interactive editing ──────────────────────────────────────────

def display_persona_traits(persona: dict) -> None:
    name = persona.get("name", "Unknown")
    header = f"── {name} "
    header += "─" * max(0, 58 - len(header))
    print(header)

    for i, (key, label, typ) in enumerate(TRAITS, start=1):
        val = persona.get(key, "")
        if isinstance(val, list):
            display = ", ".join(str(v) for v in val)
        else:
            display = str(val)
        if len(display) > 60:
            display = display[:57] + "..."
        print(f"{i:>2}. {label:<20} {display}")

    print("─" * 58)


def edit_traits_interactive(persona: dict) -> dict | None:
    working = dict(persona)

    while True:
        display_persona_traits(working)
        choice = input("\nEdit trait number, 's' to save & exit, 'b' to go back without saving:\n> ").strip()

        if choice.lower() == "s":
            return working
        if choice.lower() == "b":
            return None

        try:
            num = int(choice)
            if num < 1 or num > len(TRAITS):
                raise ValueError
        except ValueError:
            print("[Invalid — enter a number, 's', or 'b']")
            continue

        key, label, typ = TRAITS[num - 1]
        current = working.get(key, "")

        if isinstance(current, list):
            print(f"Current {label}: {', '.join(str(v) for v in current)}")
            new_val = input("New value (comma-separated): ").strip()
            if new_val:
                working[key] = [s.strip() for s in new_val.split(",") if s.strip()]
        elif typ == "float":
            print(f"Current {label}: {current}")
            new_val = input("New value (0.0–1.0): ").strip()
            if new_val:
                try:
                    v = float(new_val)
                    working[key] = max(0.0, min(1.0, v))
                except ValueError:
                    print("[Error: must be a number between 0.0 and 1.0]")
        elif typ == "int":
            print(f"Current {label}: {current}")
            new_val = input("New value: ").strip()
            if new_val:
                try:
                    working[key] = int(new_val)
                except ValueError:
                    print("[Error: must be a number]")
        else:
            print(f"Current {label}: {current}")
            new_val = input("New value: ").strip()
            if new_val:
                working[key] = new_val
