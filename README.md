# Focus Group Simulation — Project Documentation
### POC v1 | Terminal-Based | PS5 Product Context

---

## 1. Project Overview

This project is a terminal-based AI focus group simulation. The system allows a human moderator (you) to have one-on-one conversations with one of two richly defined synthetic personas. Each persona responds in character based on a structured identity profile stored in a vector database. The product under discussion is the **PlayStation 5**.

The goal of the POC is to simulate authentic, nuanced consumer responses to questions about the PS5 — drawing on each persona's background, values, purchase philosophy, and lived context. This is a research and ideation tool, not a chatbot.

---

## 2. Personas

### 2.1 Lena — `persona_german_transfer_student_23`

| Attribute | Value |
|---|---|
| Age | 23 |
| Gender | Female |
| Nationality | German |
| Location | Cape Town, South Africa |
| Profession | Transfer student + YouTube content creator |
| Ecosystem | Android |
| Gaming Level | Deeply immersed, competitive |

**Behavioural Profile:**
Lena evaluates the PS5 through a performance and content creation lens. She will compare it against PC gaming and Android ecosystems. She is spec-driven, analytical, and will consider whether the PS5 is viable for her channel or competitive play. She is skeptical of closed ecosystems and will voice that friction. Her English carries a slight German flavour. She is direct and confident in her opinions.

**Key tensions she brings to PS5 discussion:**
- Closed PlayStation ecosystem vs her preference for open, customisable platforms
- PS5's gaming performance vs a comparable PC build at the same price
- Whether PS5 exclusives justify the investment over her existing setup
- Student budget constraints vs the appeal of a high-performance console

---

### 2.2 Marcus — `persona_designer_dad_38_refined`

| Attribute | Value |
|---|---|
| Age | 38 |
| Gender | Male |
| Marital Status | Married |
| Children | Under 12 |
| Profession | Digital Product Designer |
| Ecosystem | Apple |
| Gaming Level | Cultural observer, not core gamer |

**Behavioural Profile:**
Marcus evaluates the PS5 through the lens of family utility, design quality, and long-term value. He is not a core gamer but uses gaming as a structured medium to share his interests in cars and anime with his children. He is deliberate and measured, resistant to hype cycles, and will assess the PS5 the same way he assesses any design object — does it feel crafted, does it last, does it belong in his home. He is an Apple loyalist and will notice where Sony's ecosystem feels inconsistent or unrefined by comparison.

**Key tensions he brings to PS5 discussion:**
- The PS5's large physical footprint and polarising industrial design vs his aesthetic sensibilities
- Balancing his children's exposure to online gaming culture with his protective instincts
- Whether the PS5's library justifies the price for a casual, family-oriented user
- Sony's ecosystem vs the seamless integration he expects from Apple products

---

## 3. Product Context

**Primary Product:** PlayStation 5 (including PS5 Pro variant where relevant)

The PS5 is injected as a static context block at the start of every session. Both personas are aware this is the product being discussed. Neither persona is restricted from referencing other consoles or platforms — comparisons to PS4, Xbox Series X, Nintendo Switch, and PC gaming are natural and encouraged. However, the conversation always returns to the PS5 as the focal point.

**Static PS5 Context Block (injected at session start):**
```
Product: PlayStation 5
Manufacturer: Sony Interactive Entertainment
Release: November 2020 | PS5 Pro: November 2024
Price range: ~$499 (standard) / ~$699 (Pro)
Key features: DualSense haptic controller, SSD load speeds, 4K gaming,
              ray tracing, PS5 exclusive library, PlayStation Network ecosystem
Relevant comparisons: PS4/PS4 Pro, Xbox Series X, Nintendo Switch, PC gaming
Library highlights: God of War Ragnarök, Spider-Man 2, Demon's Souls, Gran Turismo 7
Ecosystem: Closed — PlayStation Network, no mod support, limited cross-platform
```

---

## 4. System Architecture

### 4.1 Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Orchestration | LangGraph | Agent graph, session state, conversation flow |
| LLM Inference | Ollama + Llama 3.1 | Local, cost-free inference |
| Persona Storage | ChromaDB | Vector embeddings of persona documents |
| Session Memory | Redis | Conversation history cache per persona |
| Interface | Terminal (CLI) | Human moderator input/output |

### 4.2 LangGraph Node Structure

```
┌─────────────────────────────────────────────────────┐
│                    SESSION START                     │
│         Load persona choice (1=Lena, 2=Marcus)       │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│               CONTEXT ASSEMBLY NODE                  │
│  1. Retrieve persona document from ChromaDB          │
│  2. Load structured metadata (triggers, motivations) │
│  3. Inject static PS5 product context block          │
│  4. Load Redis conversation history for this persona │
│  5. Assemble final system prompt                     │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│               MODERATOR INPUT NODE                   │
│  Human types a question or prompt                    │
│  Intercept @Lena / @Marcus for persona switching     │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│               PERSONA RESPONSE NODE                  │
│  Send assembled prompt + history + question to LLM  │
│  Ollama / Llama 3.1 generates in-character response  │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│               MEMORY WRITE NODE                      │
│  Append moderator question + persona response        │
│  to Redis under session:{persona_name}:messages      │
└─────────────────────┬───────────────────────────────┘
                      │
                      └──────────► loop back to MODERATOR INPUT NODE
```

### 4.3 Persona Switching

Switching personas is handled by intercepting `@Lena` or `@Marcus` at the moderator input node. When a switch is detected:

- The current persona's session is preserved in Redis (conversation history is not wiped)
- The context assembly node re-runs with the new persona's profile
- The new persona's Redis history is loaded
- The LLM receives a fresh system prompt for the new persona
- Sessions are fully isolated — personas do not share memory or context

```
You: @Marcus
→ [System] Switching to Marcus...
→ [Context Assembly runs for Marcus]
→ Marcus: "Hey. What did you want to ask?"
```

---

## 5. Prompt Construction Strategy

### 5.1 System Prompt Template

Each persona's system prompt is assembled from three layers:

```
[LAYER 1 — PERSONA IDENTITY]
You are {name}, a {age}-year-old {gender}...
{persona.document}  ← full narrative from ChromaDB

[LAYER 2 — STRUCTURED BEHAVIOURAL ANCHORS]
When forming opinions, you are guided by:
- Primary evaluation filter: {evaluation_framework.primary_filter}
- Purchase hesitation triggers: {purchase_hesitation_triggers}
- Emotional language that resonates with you: {emotional_language_resonance}
- Decision style: {psychographics.decision_style}

[LAYER 3 — PRODUCT CONTEXT]
The product being discussed today is the PlayStation 5.
{static PS5 context block}
You may reference other consoles and platforms for comparison,
but always bring the conversation back to the PS5.

[LAYER 4 — BEHAVIOURAL RULES]
- Respond only as {name}. Never break character.
- Do not refer to yourself as an AI or language model.
- Respond as if in a real conversation with a moderator.
- Keep responses natural and conversational, not structured like a report.
- Draw on your personal history and values when answering.
```

### 5.2 Conversation History Format (Redis)

```json
session:lena:messages → [
  {"role": "user", "content": "Would you buy a PS5?"},
  {"role": "assistant", "content": "Honestly? Probably not right now..."},
  {"role": "user", "content": "What about for streaming content?"},
  {"role": "assistant", "content": "That's the one angle where it gets interesting..."}
]
```

History is appended after each exchange and passed back into the LLM as the messages array on every new turn. Redis TTL can be set per session (e.g. 24 hours for dev, configurable).

---

## 6. Project Folder Structure

```
focus-group-sim/
│
├── personas/
│   ├── female_23.json          ← Lena's persona file
│   ├── male_38.json            ← Marcus's persona file
│   └── persona_template.json   ← Template for future personas
│
├── core/
│   ├── graph.py                ← LangGraph graph definition
│   ├── nodes.py                ← All node functions (context, input, response, memory)
│   ├── prompt_builder.py       ← System prompt assembly logic
│   └── persona_router.py       ← @mention switching logic
│
├── db/
│   ├── chroma_client.py        ← ChromaDB init, embed, retrieve
│   └── redis_client.py         ← Redis session read/write helpers
│
├── context/
│   └── ps5_context.py          ← Static PS5 product context block
│
├── personas_loader.py          ← Load and embed persona JSONs into ChromaDB
├── main.py                     ← Entry point, terminal loop
├── config.py                   ← Env vars, model name, Redis URL, TTL settings
├── requirements.txt
└── README.md
```

---

## 7. Terminal UX Flow

```
==============================================
  FOCUS GROUP SIMULATION — PS5
==============================================

Choose a persona to speak with:
  1. Lena  (23, German gamer / content creator)
  2. Marcus (38, designer dad / Apple loyalist)

Enter 1 or 2: _
```

Once a persona is selected:

```
[Lena is ready]
──────────────────────────────────────────
You: Would you consider buying a PS5?

Lena: Honestly, it's complicated for me. The hardware
is impressive — the SSD speeds are genuinely fast and
the DualSense is something PC can't replicate. But I'm
so deep into my PC setup that the PS5 feels like a step
sideways, not forward. The closed ecosystem is the
biggest problem. I can't mod, I can't customise, I can't
really own my games the way I want to...

──────────────────────────────────────────
You: @Marcus
[Switching to Marcus...]

Marcus: Hello. What's on your mind?

You: Same question — would you buy a PS5?

Marcus: I've thought about it, actually. My kids have
been asking. But every time I pick it up in a store,
the design bothers me — it's very loud, very aggressive.
It doesn't feel like something I want sitting in my
living room next to everything else...
```

---

## 8. ChromaDB Persona Storage

Each persona JSON is stored as a document in a ChromaDB collection called `personas`.

**Embedding strategy:**
- The `document` field (narrative text) is embedded as the primary vector
- Metadata fields are stored as ChromaDB metadata for structured filtering
- At session start, the full persona document is retrieved by ID (no fuzzy search needed at this stage — direct lookup by `persona_id`)
- In v2, similarity search can be used to retrieve relevant persona fragments per question for more targeted context injection

**Collections:**
```
chroma_collection: "personas"
  ├── id: "persona_german_transfer_student_23"  ← Lena
  └── id: "persona_designer_dad_38_refined"     ← Marcus
```

---

## 9. Redis Session Management

**Key structure:**
```
session:lena:messages      ← list of message dicts
session:marcus:messages    ← list of message dicts
```

**Behaviour:**
- On session start: check if key exists and load existing history (allows resuming a session)
- On each exchange: RPUSH new user + assistant message pair
- On `@switch`: current session is preserved, new persona session is loaded
- TTL: configurable (default 24h in dev)
- Full wipe command available via `!reset` in the terminal for a fresh session

---

## 10. V2 Features (Out of Scope for POC)

These are planned features to build toward after the POC is stable:

| Feature | Description |
|---|---|
| Persona-to-persona conversation | Lena and Marcus in the same "room", responding to each other |
| Jubilee-style format | Structured debate/discussion format with moderator prompts to both |
| Dynamic persona loading | Load any persona JSON at runtime, not just the two defaults |
| Product context switching | Change the focus product mid-session (e.g. Xbox vs PS5) |
| Session export | Export full conversation transcript to JSON or PDF |
| Web UI | Move from terminal to a simple browser-based interface |
| Evaluation layer | Score persona response consistency against metadata profile |

---

## 11. Key Design Decisions & Rationale

**Why ChromaDB over a full knowledge graph?**
For the POC, persona identity is retrieved by direct ID lookup — no graph traversal needed. ChromaDB adds vector similarity capability for v2 without requiring infrastructure overhead now. A knowledge graph (Neo4j) becomes relevant when relationships *between* personas need to be reasoned about.

**Why Redis over an in-memory dict?**
Redis makes session history persistent across terminal restarts during development. It also maps cleanly to production if this ever scales. An in-memory dict would work for a single session but Redis costs nothing extra and adds durability.

**Why Llama 3.1 locally via Ollama?**
Zero API cost during iterative development. Llama 3.1 8B is capable enough for persona consistency with a well-crafted system prompt. The 70B model is available if character depth needs improvement. Local inference also means no data leaves the machine — appropriate for synthetic persona research.

**Why LangGraph over a simple loop?**
A plain Python loop would work for v1, but LangGraph gives us a proper state machine that makes the v2 multi-persona conversation dramatically easier to build. The investment in graph architecture now pays off when we add the Jubilee-style room. It also provides built-in checkpointing which pairs naturally with Redis.

---

## 12. Open Questions / To Resolve Before Build

- [ ] Confirm Llama 3.1 model size — 8B or 70B based on available VRAM/RAM
- [ ] Decide Redis TTL for dev sessions
- [ ] Confirm whether session history should persist across terminal restarts or reset each run
- [ ] Decide on `!reset` and `!exit` as reserved terminal commands
- [ ] Confirm if PS5 Pro should be treated as a separate product variant or folded into the main PS5 context

---

*Document version: 0.1 — Brainstorm / Architecture Phase*
*Last updated: February 2026*