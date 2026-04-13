# Next-Step AI — Phase 1 Blueprint

## What Is This?

A complete set of instructions for building Next-Step AI Phase 1.
Give this entire folder to a coding agent (Claude Code, Cursor, Copilot, or a developer) and they can build the system without any additional context.

## Reading Order

| Order | File | What It Contains |
|-------|------|-----------------|
| 1 | `SOUL.md` | Product identity, principles, non-negotiable rules |
| 2 | `SKILL.md` | Tech stack, project structure, coding conventions, what NOT to build |
| 3 | `docs/ARCHITECTURE.md` | System design, agent contracts, data flow diagrams, error recovery |
| 4 | `schemas/SCHEMAS.md` | Database tables, data contracts between agents, extraction rules |
| 5 | `prompts/PROMPTS.md` | All LLM prompts with design rationale |
| 6 | `profiles/founder.md` | Static user profile for Phase 1 testing |
| 7 | `tests/TESTING.md` | Unit tests, quality evaluation framework, success criteria |
| 8 | `TASKS.md` | Step-by-step build order with verification steps |

## Quick Start for the Building Agent

```
1. Read files 1-8 in order above
2. Follow TASKS.md exactly — it has 17 tasks in 5 phases
3. Each task has a verification step — pass it before moving on
4. Do NOT build anything from Phase 2 (listed in SKILL.md under "What NOT to Build")
5. All prompts are in prompts/ — use them as-is, do not modify
6. Test with the unit tests in tests/TESTING.md
```

## Tech Stack Summary

- Python 3.11+
- Streamlit (UI)
- SQLite (storage)
- Anthropic API (Claude — for Insight Agent + optional base model)
- OpenAI API (GPT — for Synthesis Composer + optional base model)
- No LangChain, no vector DB, no graph DB in Phase 1

## The One Hypothesis Being Tested

> Can an Observer layer reliably generate genuinely useful missing angles
> that change how the user thinks, decides, or asks their next question?

30 real interactions. Self-rated quality scores. Defined success criteria.
Everything else is Phase 2.
