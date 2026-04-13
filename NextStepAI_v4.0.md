# **Next-Step AI**
**Internal Vision & Development Document**
Version 4.0 — Confidential, Internal Use Only | April 2026

## **1. Core Problem**
AI systems are increasingly useful, but usefulness is not the same as partnership.

Current models are optimized to respond, complete, and assist. They are not inherently designed to:
* detect what the user has not considered,
* separate truth from user preference,
* maintain a stable understanding of the user over time,
* or improve the user's next question rather than only completing the current one.

* **1. Weak-question trap** — A model can produce a correct answer to an incomplete question. The result may still be strategically wrong because the user asked from within the limits of their own knowledge.
* **2. Sycophancy and over-agreeableness** — Models often optimize for approval, alignment, and conversational smoothness. This can reward confirmation rather than correction.
* **3. Cognitive offloading without scaffolding** — When AI is poorly designed, it can reduce vigilance, compress reflection, and turn thinking into passive consumption.

**The Problem This Product Solves**

**The user cannot reliably see what they do not yet know to ask, compare, challenge, or verify.**

This is not a universal assistant. It is a cognitive support layer focused on revealing missing angles, hidden assumptions, and structurally better next questions.

## **2. Product Vision**
Next-Step AI is a personal knowledge and review layer that works above any capable base model.

* It does not replace the host model.
* It does not rewrite the host answer.
* It does not compete with the model at the answer layer.

*The model answers. Next-Step AI observes what changed, what may be missing, and what is worth surfacing later through a report, alert, or on-demand analysis.*

**Core Product Promise**

* better next questions,
* better framing,
* better awareness of gaps,
* and better cumulative understanding of how the user thinks, decides, and learns.

**Product Identity**

Next-Step AI is not a reviewer, not an evaluator, and not a chatbot. It is a **knowledge partner** — closer to a coach who opens doors for exploration and a consultant who provides the right tools to walk through them.

It does not evaluate the AI model's performance. It does not grade the user's questions. It reads conversations the user had with any AI model, understands the topics being explored, and does three things:

1. Opens doors the user didn't know existed — concepts, tools, standards, adjacent domains they haven't encountered yet
2. Consolidates scattered questions into structured, powerful prompts that produce better answers
3. Generates contextual instructions that guide the AI model to respond with more depth and less drift

The core promise remains: **helping the user ask about what they don't know they don't know.**

## **3. What "Elevation" Means**
**Revealing useful missing angles that materially improve the user's next exploration, next framing, or next decision path.**

Elevation is not: poetic insight, generic reflection, flattering personalization, or broader wording for the same thought.

**Types of Value Next-Step AI Provides**

* **Exploration Doors** — concepts, tools, frameworks, or adjacent domains the user hasn't encountered. Not criticism of what was missed, but opening of what could be explored. Example: "The problem you're solving has a tool called X that does exactly this — here's how to explore whether it fits."
* **Informational Gaps** — a missing concept, standard, or domain fact directly relevant to the topic. Same as before.
* **Inferential Conflicts** — a hidden assumption or contradiction with prior context. Same as before.
* **Complementary Dimensions** — an adjacent domain required for better execution or decision quality. Same as before.
* **Pattern Signals** — observable tendencies across multiple conversations over time. NOT from a single conversation. Requires: 3+ independent instances across 2+ conversations. From a single conversation, use "signal" or "tentative observation" only.

## **4. What Makes Next-Step AI Different**
| System Type | What It Lacks |
| --- | --- |
| **Chat assistants** | Answer well, but lack structured long-term user modeling and reliable missing-angle surfacing |
| **Memory tools** | Store everything, but do not decide what matters cognitively |
| **Personal AI companions** | Often optimize for tone, warmth, or engagement rather than truth and structural challenge |
| **Knowledge capture systems** | Preserve information, but do not reason over how the user thinks, learns, or repeats patterns |

**It is a review-and-guidance layer that uses memory and structured maps to improve the user's next move.**

## **5. Product Shape — What the User Actually Experiences**
Next-Step AI is NOT a chat interface. The user does not type questions into Next-Step AI and get answers.

Instead:

1. The user has conversations with any AI model (Claude, GPT, Gemini, or any other) through their normal workflow
2. The user imports these conversations into Next-Step AI (paste, upload file, or future: automatic capture)
3. Next-Step AI processes the conversations in the background:
   * Parses and separates user messages from AI responses
   * Compresses AI responses to structured summaries (what was covered, recommended, warned about, admitted as unknown) while keeping user messages fully intact
   * Analyzes the full set of conversations for exploration doors, gaps, conflicts, and patterns
   * Connects findings to the user's maps (when available)
   * Conducts contextual deep research to discover what the conversations didn't surface
4. The user receives:
   * **Analysis Report**: findings ranked by impact with evidence and confidence levels
   * **Ready Prompts**: complete, paste-ready prompts with strict rules — not generic follow-up questions
   * **Contextual Instructions**: temporary instructions tailored to the specific topic, designed to be used with the Ready Prompts in a new conversation to prevent AI drift and bias

**The user's conversation with AI stays natural and uninterrupted. Next-Step AI works after, not during.**

## **6. High-Level Architecture**
**Figure 1 — Full Architecture Overview**

The base model is replaceable. The stable layer is Next-Step AI itself: memory stack, maps, insight logic, review policy, and report composition.

**Core Agents**

* **Conversation Parser** — parses imported conversations into structured messages, separates user messages from AI responses, detects conversation format automatically
* **Conversation Compressor** — compresses AI responses to 4 structured elements (covered, recommended, warned, unknown) while preserving user messages fully intact. Uses a lightweight model (e.g., Claude Haiku) for cost efficiency
* **Memory Agent** — stores conversations, canonical units, and maintains all memory layers
* **Insight Agent** — analyzes full conversation sets (not individual Q&As) against user profile and maps. Generates exploration doors, gaps, conflicts, and pattern signals
* **Research Agent** — NEW: conducts contextual deep research based on conversation topics. Discovers tools, standards, concepts, and developments the user hasn't encountered. This is what enables the "unknown unknowns" — finding what doesn't appear in the conversation at all
* **Context Agent** — builds focused context for the Insight Agent from memory and maps
* **Prompt Architect** — NEW: builds complete Ready Prompts with goals, structure requirements, and strict rules. Also generates Contextual Instructions tailored to each topic
* **Synthesis Composer** — assembles the final report from all agent outputs
* **Calibration Agent** — corrects map drift over time

**Separation Principle**

The base answer remains the responsibility of the host model. Next-Step AI must not merge itself into the answer generation path by default.

**Partner Principle**

Next-Step AI does not evaluate the AI model's quality. It does not grade the user's questions. It opens doors, provides tools, and leaves the decision to the user. The tone is that of a knowledgeable partner, not a judge.

## **7. Memory Stack**
**Figure 2 — Memory Stack: 6 Layers & Promotion Policy**

**Layer 1 — Raw Memory**

The primary source of truth. Stores: imported conversations (full original text + compressed version), user corrections, external sources (LinkedIn/CV/GitHub when available). Each conversation carries: label, source model, import date, word count, compression ratio, analysis status (pending/analyzed).

**Layer 2 — Canonical Memory**

Converts raw interaction into structured units: entities, decisions, tasks, claims, open questions. Question: What are the meaningful units?

**Layer 3 — Graph Relation Layer**

Links between canonical units with strength, time, and confidence. States: candidate, weak, confirmed, strong, decaying, stale. Question: How strong is each relation?

**Layer 4 — Derived Maps**

Three maps: Cognitive, Behavioral, Personal. Always structured hypotheses with confidence — not ground truth. Question: What do patterns suggest about the person?

**Layer 5 — Current Topic Model**

Live model of the current discussion. Contains: topic, goal, open questions, pending decisions, risk flags. Question: What is the current topic missing?

**Layer 6 — Delta Layer**

A structured record of what changed since the last report. Contains: map updates, new links, new hypotheses, resolved patterns. Question: What is new?

*Without the Delta Layer, reports become repetitive state descriptions instead of useful change summaries.*

## **8. The Three Maps**
**8.1 Cognitive Map**
What the user knows, does not know, or assumes without enough scrutiny. Includes: knowledge strengths, recurring gaps, hidden assumptions, topic depth.

**8.2 Behavioral Map**
What the user actually does over time. Includes: repeated decision patterns, abandonment patterns, pressure responses, action vs delay patterns.

**8.3 Personal Map**
How the user thinks, communicates, and receives guidance. Includes: communication style, response to challenge, argument-building style, value anchors.

**Maps must never be treated as unquestionable truths. They are living, revisable structures.**

## **9. Graph Access Policy**
| Agent | Access Level |
| --- | --- |
| **Conversation Parser** | no graph access — parsing only |
| **Conversation Compressor** | no graph access — compression only |
| **Research Agent** | relevant graph-derived context through resolver — to inform what to research based on user's known domains |
| **Prompt Architect** | relevant graph-derived evidence — to build profile-aware prompts and instructions |
| **Memory Agent** | Deepest access: storage, linking, weakening, promotion, correction |
| **Insight Agent** | Relevant graph-derived evidence through resolver — not full raw graph |
| **Context Agent** | Focused retrieval view only — context assembly, not graph interpretation |
| **Calibration Agent** | Broad audit access — evaluates prior inferences for weakening or removal |

## **10. Agent Roles and Contracts**

|  |
| --- |
| **Conversation Parser** |
| **Purpose** | Parse imported conversations into structured user/assistant message pairs |
| **Inputs** | Raw conversation text (paste or file) |
| **Outputs** | Structured message list with role, content, and detected format |
| **Allowed** | Parse, detect format, separate roles, handle multiple formats (ChatGPT, Claude, Gemini, generic, Arabic) |
| **Forbidden** | Summarizing, analyzing, filtering, or modifying content |

|  |
| --- |
| **Conversation Compressor** |
| **Purpose** | Compress AI responses while preserving user messages fully intact |
| **Inputs** | Parsed message list |
| **Outputs** | Compressed conversation (user messages unchanged + AI responses as 4-element summaries) |
| **Allowed** | Compress AI responses to: covered, recommended, warned, unknown |
| **Forbidden** | Modifying user messages, removing content without compression, making analytical judgments |
| **LLM** | YES — lightweight model (Claude Haiku) for cost efficiency |

|  |
| --- |
| **Research Agent** |
| **Purpose** | Discover tools, standards, concepts, and domain knowledge not present in the conversations |
| **Inputs** | Conversation topics, user profile, map-derived context |
| **Outputs** | Discovery list with relevance scores and evidence |
| **Allowed** | Web search, domain-specific research, tool discovery, standard/regulation lookup |
| **Forbidden** | Modifying maps, making surfacing decisions, generating user-facing content directly |

|  |
| --- |
| **Prompt Architect** |
| **Purpose** | Build complete Ready Prompts and Contextual Instructions from analysis findings |
| **Inputs** | Insight Agent findings, Research Agent discoveries, user profile, maps |
| **Outputs** | Ready Prompts (with goals, structure, rules) + Contextual Instructions (topic-specific) |
| **Allowed** | Build prompts, set rules, define structure, adapt to user's communication style |
| **Forbidden** | Generating analysis, modifying findings, deciding what to surface |

|  |
| --- |
| **Insight Agent** |
| **Purpose** | Generate hypotheses from maps, topic state, and accumulated changes |
| **Inputs** | Compressed conversations (full set, not individual Q&As), user profile, maps, Research Agent discoveries |
| **Outputs** | Exploration doors, informational gaps, inferential conflicts, complementary dimensions, pattern signals (with confidence levels and evidence sufficiency checks), question quality observations |
| **Allowed** | Cross-reference across multiple conversations, detect question patterns, identify exploration opportunities, score confidence, estimate routing class |
| **Forbidden** | Evaluating the AI model's performance, grading the user's question quality as good/bad, claiming patterns from single conversations, modifying maps |

|  |
| --- |
| **Memory Agent** |
| **Purpose** | Maintain the full memory stack and enforce transition rules |
| **Inputs** | Parsed and compressed conversations, user deletion or correction requests |
| **Outputs** | Updated Raw, Canonical, Graph, Derived Maps, Topic Model, Delta Layer |
| **Allowed** | Store · extract canonical units · update graph links · maintain delta records · apply deletion rules |
| **Forbidden** | Using maps to filter what enters Raw · making review/report decisions · circular inference |

|  |
| --- |
| **Context Agent** |
| **Purpose** | Assemble focused context for the Insight Agent and Research Agent |
| **Inputs** | Current conversation topics, relevant findings, focused retrieval from memory via resolver |
| **Outputs** | Dynamic system prompt, focused context pack (500–800 tokens) |
| **Allowed** | Retrieve · compress · prioritize · build bounded context |
| **Forbidden** | Generating new insight · updating maps · deciding on reports or alerts |

|  |
| --- |
| **Synthesis Composer** |
| **Purpose** | Turn approved findings into a coherent artifact |
| **Inputs** | Insight Agent findings, approved findings, delta layer, personal map for delivery style |
| **Outputs** | Analysis Report · Ready Prompts · Contextual Instructions · On-demand Analysis |
| **Allowed** | Synthesize · format · group deltas · produce structured questions · adapt tone |
| **Forbidden** | Changing policy decisions · adding unsupported claims · rewriting base answer |

|  |
| --- |
| **Calibration Agent** |
| **Purpose** | Correct map drift, weaken unsupported patterns, and reduce structural illusion |
| **Inputs** | User feedback, graph links, map state, delta history, review outcomes |
| **Outputs** | Confidence adjustments · weakened links · correction flags · stale pattern removals |
| **Allowed** | Weaken · flag · request confirmation · decay stale inferences |
| **Forbidden** | Silently delete high-impact items · strengthen claims without fresh evidence · alter Raw history |

## **11. Review and Routing Logic**

Since Next-Step AI now analyzes imported conversations (not live interactions), the real-time Observer routing system (Class A/B/C/D) is replaced with a simpler output priority system:

**Finding Priority Levels:**
- **Immediate relevance**: directly affects what the user is actively working on right now
- **Strategic relevance**: important for the user's broader goals but not time-sensitive
- **Exploratory**: worth knowing but the user decides whether to pursue

All findings appear in the report, ordered by priority. There are no real-time alerts in this architecture.

**11.1 Insight → Output Boundary**

**Insight owns: analysis. Synthesis owns: format. No agent crosses into the other's domain.**

## **12. Promotion and Confidence Policy**
* **Level 1 — Graph Candidate:** tentative relation only — not enough to update a map.
* **Level 2 — Topic Eligible:** can influence retrieval and Topic Model — not enough for personal inference.
* **Level 3 — Map Eligible:** subject to strict rules: evidence strength + source diversity + temporal stability + user confirmation.

| Target Layer | Threshold |
| --- | --- |
| **Topic Model** | Lower — temporary and revisable |
| **Cognitive Map** | Moderate — recurring evidence in related domains |
| **Behavioral Map** | High — repeated behavior across time and contexts |
| **Personal Map** | Highest — strong evidence, low contradiction, often user confirmation |

*Abstention principle: when confidence is not strong enough, keep the signal in candidate state rather than forcing an identity-level update.*

**Confidence Levels (Required for every finding)**

- **tentative**: single instance, single conversation, limited evidence
- **moderate**: multiple instances in same conversation, or consistent with user profile
- **high**: multiple conversations, multiple instances, clearly demonstrated

**Evidence Sufficiency Check (Mandatory before every finding)**

Before outputting any finding, the system must verify:
1. Is the evidence sufficient for the level of claim being made?
2. Is this describing what was SEEN in the text, or what was INFERRED beyond it?
3. Is this about the CONVERSATION content, or a claim about the PERSON?
4. Could someone disagree with this finding based on the same evidence?

**Impact Calibration**
- Maximum 1 HIGH impact finding per analysis
- HIGH = not addressing this will cause measurable failure
- MEDIUM = improves quality but doesn't prevent failure
- LOW = adds depth but doesn't change the decision

## **13. Evaluation Principles**
**13.1 Missing-Angle Quality**
* reveals a real hidden assumption,
* adds a non-obvious and relevant missing constraint,
* changes the next question in a more useful direction,
* improves decision framing,
* or closes a meaningful blind spot.

**13.2 Anti-Filler Protection**
Test against: novelty without leverage, broader wording with no new content, elegant but obvious suggestions, curiosity inflation.

**Surprise Test**: If the user said "I already know this" — would that genuinely surprise the system? If not, the finding is filler.

**Evidence Threshold for Claims**:
- "Pattern" / "recurring" → requires 3+ instances across 2+ conversations
- "Contradiction" → requires 2 directly opposing statements with evidence
- "Signal" / "tentative observation" → acceptable from single conversation
- Never use "consistent behavior" without 5+ instances across 3+ conversations

**13.3 Anti-Sycophancy Protection**
User approval cannot be the dominant optimization signal. Test for: reassurance bias, agreement drift, comfort-first outputs.

**13.4 Dependency Risk**
Evaluate whether the user becomes more self-correcting, better at stronger questions, and less likely to outsource reflection entirely.

## **14. MVP Strategy**

**Build Now:**
* Conversation import (paste + file upload)
* Conversation parser (multi-format detection)
* Conversation compressor (user messages intact, AI responses to 4 elements)
* Session-level Insight Agent (analyzes full conversation sets)
* Research Agent (contextual deep research connected to conversation topics — Phase 1 starts with web search for tools, standards, and domain concepts relevant to conversation topics. Expands to deeper research capabilities in later phases.)
* Prompt Architect (Ready Prompts with rules + Contextual Instructions)
* Synthesis Composer (structured reports)
* SQLite memory (conversations + canonical units + insights + reports)
* Streamlit UI (Import, Analysis, Insights Browser, Settings)
* Static user profile (founder.md — replaced by maps in Phase 2)
* Confidence levels and evidence sufficiency checks on all findings

**Postpone**
* full psychological modeling,
* aggressive personalization,
* continuous decay-rate learning,
* automatic per-user prompt evolution,
* identity-level inference without confirmation,
* Automatic conversation capture from platforms (API integrations)
* INSPIRE as live per-conversation layer (requires maps foundation first)

**MVP Goal**
Prove the system can generate: useful report-worthy findings, better next questions, low-noise reflective reports, and improved framing without increasing annoyance or dependence.

## **15. Failure Modes**
| Failure Mode | Description |
| --- | --- |
| **15.1 Novelty Theater** | Generates clever-looking questions that expand discussion without improving outcomes. |
| **15.2 Toxic Mirror** | Personalization reflects comfort and preference rather than truth and structural challenge. |
| **15.3 Map Overconfidence** | Weak evidence gets promoted into stable user claims. |
| **15.4 Changelog Spam** | Delta Layer becomes a noisy dump instead of a meaningful report. |
| **15.5 Silent Dependency** | The user becomes better at consuming reports, but worse at independent framing. |
| **15.6 Routing Failure** | The system delays urgent findings or escalates weak ones. |
| **15.7 Content Analysis Trap** | The system analyzes what's missing from the conversation content instead of what's missing from the user's thinking and exploration. Mitigation: Research Agent actively searches beyond the conversation. Findings must open new doors, not just note content gaps. |
| **15.8 Generic Prompt Syndrome** | Ready Prompts are well-structured but could be written by anyone without reading the conversation. Mitigation: Every Ready Prompt must reference specific context from the analyzed conversations. Test: could this prompt exist without this conversation? If yes, it fails. |

## **16. Non-Negotiable Design Principles**
* **16.1 Truth Before Personalization** — personalization changes delivery, not reality.
* **16.2 Separation of Layers** — the base answer remains untouched. Review and reporting happen after.
* **16.3 Conservative Inference** — prefer candidate state over false certainty.
* **16.4 Report Over Interruption** — default to delayed reflection unless urgency justifies alerting.
* **16.5 Auditability** — every high-impact claim traceable to evidence.
* **16.6 Calibration Over Confidence Theater** — weaken, retract, and ask for confirmation rather than defend inference.
* **16.7 Partner Over Judge** — Next-Step AI does not evaluate the AI model, does not grade the user. It opens doors, provides tools, and leaves the decision to the user. The tone is that of a knowledgeable partner and coach — not a reviewer or assessor.

## **17. A Regular Day with Next-Step AI**
| Moment | What Happens |
| --- | --- |
| **Morning** | User had a long conversation with GPT about a project proposal. Copies and pastes it into Next-Step AI. |
| **Also morning** | User uploads a Claude conversation about a technical decision from yesterday. |
| **Before lunch** | User clicks "Analyze." Next-Step AI: parses both conversations, compresses AI responses, runs Insight Agent across both, Research Agent discovers a relevant tool and a new regulation the user didn't know about, Prompt Architect builds 3 Ready Prompts with contextual instructions. |
| **After lunch** | User reads the report. One finding opens a door they genuinely didn't know existed. They paste a Ready Prompt into a new Claude conversation with the contextual instructions. The response is noticeably deeper and more structured than their usual interactions. |
| **End of day** | User adds a third conversation from Gemini. Runs analysis again. This time the system notices a pattern across all three conversations and connects it to the user's profile. |

**What's different from a day without it:**
* The user didn't spend 45 minutes discovering something that the system surfaced in 30 seconds
* The Ready Prompts produced answers the user couldn't have gotten with their usual question style
* The system noticed a cross-conversation pattern the user couldn't see because they were inside each conversation separately

## **18. Open Questions**
* 1. What evaluation framework best distinguishes useful missing angles from clever filler?
* 2. What cadence is best by default: daily, end-of-session, breakpoint, or user-scheduled?
* 3. What minimum model capability is required for useful Insight generation?
* 4. What promotion thresholds are safe enough for each map?
* 5. How should routing classes evolve after MVP?
* 6. What is the right balance between explicit user-confirmed profile and inferred maps?
* 7. How should Delta Layer ranking be implemented so reports stay compact and useful?
* 8. How do we measure whether the product reduces or increases cognitive dependence?
* 9. When does any form of fine-tuning or prompt optimization become justified?
* 10. How do we prevent interaction feedback from optimizing toward pleasingness rather than epistemic value?
* 11. Does Graphiti/Zep natively support Delta Layer tracking or does it require custom logic?
* 12. What is the minimum confidence threshold for Graph → Derived Maps promotion?
* 13. Technical wrapper details: user via direct platforms vs API key — to be discussed separately.
* 14. What is the minimum depth of contextual research needed for the Research Agent to surface genuinely unknown tools/concepts?
* 15. How should the Conversation Compressor handle conversations in mixed languages (Arabic + English)?
* 16. What formats should the parser support beyond plain text? (JSON exports from ChatGPT, Claude, etc.)
* 17. How do Ready Prompts and Contextual Instructions interact — are they always used together or independently?
* 18. At what point does INSPIRE transition from onboarding protocol to live per-conversation layer?

## **19. Connection to Existing Projects**
*This section is for internal use only — not shared externally.*

| Project | Its Role in Next-Step AI |
| --- | --- |
| **INSPIRE Framework** | Phase 1: Onboarding protocol — builds initial maps. Future: Live per-conversation layer that generates topic-specific instructions based on conversation analysis and user maps — not just onboarding but continuous contextual guidance. |
| **CRAFTS Framework** | Methodology for building initial Insight Prompt — the Seed Prompt that GEPA+DSPy starts from |
| **HVA** | Voice layer — understands tone and emotional state to inform routing class estimates |
| **Guardian-H** | Context management and project memory between sessions — feeds the Delta Layer |
| **OpenJarvis (Stanford)** | Potential foundation for local infrastructure — could eliminate building from scratch |
| **GEPA + DSPy** | Automatic Insight Prompt improvement per user — dedicated research conversation pending |

**These are not separate projects — they are layers of one system.**

## **20. Final Product Thesis**
Next-Step AI should not try to be the smartest voice in the room.

**It should try to become the layer that notices what would otherwise be missed.**

* the next question,
* the next framing,
* the next comparison,
* the next decision,
* **the next exploration the user didn't know they needed.**

**Its value is that it helps the user see what was absent from their current map.**

## **21. The Discovery Moment — Why This Project Exists**
*This section is for personal internal use only. Written April 4, 2026.*

**21.1 The Sentence That Opened Everything**
**If I knew what I wanted to discover, I wouldn't need you to ask — because I would ask directly.**

**21.2 The Illusion the Founder Discovered in Himself**
The founder is building a product that frees people from the illusion of false understanding — while the instructions he built have themselves become constraints rather than a tool. This is not failure — it is living proof that the problem is real.

**21.3 What This Means for the Product**
Next-Step AI will not succeed because it improves questions — but because it sees the missing angles the user cannot see in their own thinking.

**21.4 The Founder's Cognitive Map**
* **Strength:** building conceptual frameworks, detecting contradictions, strategic thinking.
* **Gaps:** direct programming implementation, resolving the boundary between ambition and execution.
* **Most dangerous hidden assumption:** complete understanding is a prerequisite for action.
* **Pattern to watch:** trusts analysis more than experimentation.

*Next-Step AI — Version 4.0 — Internal Use Only*
