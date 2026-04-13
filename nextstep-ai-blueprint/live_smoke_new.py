import asyncio
import os
import sys
import traceback
import json
import datetime
from unittest.mock import patch

from config import DB_PATH, REPORTS_DIR
import database.db as db
import agents.memory as memory
from orchestrator import analyze_and_report
import anthropic.resources.messages

RAW_INSIGHT_TEXT = None
RAW_RESEARCH_DATA = None

_orig_msg_create = anthropic.resources.messages.Messages.create

def mock_msg_create(self, *args, **kwargs):
    global RAW_INSIGHT_TEXT
    from config import INSIGHT_MODEL
    try:
        res = _orig_msg_create(self, *args, **kwargs)
        if kwargs.get("model") == INSIGHT_MODEL:
            RAW_INSIGHT_TEXT = res.content[0].text
        return res
    except Exception as e:
        traceback.print_exc()
        raise e

async def run_tests():
    global RAW_INSIGHT_TEXT

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    db.init_db()

    print("══════════════════════════════════════════════════")
    print("TEST 1: Add a conversation via paste")
    print("══════════════════════════════════════════════════")
    conv1 = "User: How do I build a Temporal Knowledge Graph?\nClaude: You use Subject-Predicate-Object-Time."
    id1 = memory.add_conversation("TKG Basics", "Claude", conv1)
    c1 = memory.get_conversation(id1)
    pending = memory.get_pending_conversations()
    print(f"Added ID: {id1}\nStatus: {c1['status']}\nTotal Pending: {len(pending)}\n")

    print("══════════════════════════════════════════════════")
    print("TEST 2: Add a second conversation")
    print("══════════════════════════════════════════════════")
    conv2 = "User: How to resolve conflicts in TKG?\nGPT: You can use versioning schemas."
    id2 = memory.add_conversation("TKG Conflicts", "GPT", conv2)
    pending = memory.get_pending_conversations()
    print(f"Added ID: {id2}\nTotal Pending: {len(pending)}\n")

    print("══════════════════════════════════════════════════")
    print("TEST 3 & 4: Analyze All Pending & Verify Report")
    print("══════════════════════════════════════════════════")
    RAW_INSIGHT_TEXT = None
    with patch("anthropic.resources.messages.Messages.create", mock_msg_create):
        with patch("agents.research.research_topic") as mock_research:
            mock_research.return_value = {
                "discoveries": [
                    {
                        "title": "RDF-star",
                        "type": "standard",
                        "relevance": "Modern standard for expressing statements about statements in knowledge graphs",
                        "source": "W3C",
                        "suggested_angle": "Could simplify TKG conflict resolution with built-in reification"
                    }
                ],
                "research_summary": "Found W3C RDF-star standard relevant to Temporal Knowledge Graphs",
                "search_queries_used": ["temporal knowledge graph standards", "TKG tools"]
            }
            report, contextual_instructions, research_data = await analyze_and_report()

    print("── Insight Agent RAW JSON Response ──")
    print(RAW_INSIGHT_TEXT)

    print("\n── Final Report ──")
    print(report)

    print("\n── Contextual Instructions ──")
    print(contextual_instructions)

    print("\n── Research Data ──")
    print(research_data)
    
    print("\n══════════════════════════════════════════════════")
    print("TEST 5: Verify conversations marked as analyzed")
    print("══════════════════════════════════════════════════")
    c1 = memory.get_conversation(id1)
    c2 = memory.get_conversation(id2)
    pending = memory.get_pending_conversations()
    print(f"Conv 1 Status: {c1['status']}")
    print(f"Conv 2 Status: {c2['status']}")
    print(f"Remaining Pending: {len(pending)}\n")

    print("══════════════════════════════════════════════════")
    print("TEST 6: Add a third conversation and analyze again")
    print("══════════════════════════════════════════════════")
    conv3 = "User: Tell me a joke.\nGemini: Why did the chicken..."
    id3 = memory.add_conversation("Random Joke", "Gemini", conv3)
    pending_before = memory.get_pending_conversations()
    print(f"Pending before new analysis: {len(pending_before)} (should be 1)")
    
    RAW_INSIGHT_TEXT = None
    with patch("anthropic.resources.messages.Messages.create", mock_msg_create):
        with patch("agents.research.research_topic") as mock_research:
            mock_research.return_value = {"discoveries": [], "research_summary": "No relevant findings", "search_queries_used": []}
            report2, ci2, research2 = await analyze_and_report()

    print("\n── Insight Agent RAW JSON for Round 2 ──")
    print(RAW_INSIGHT_TEXT)

    print("\n── Final Report Round 2 ──")
    print(report2)

    print("\n── Contextual Instructions Round 2 ──")
    print(ci2)

    print("\n── Research Data Round 2 ──")
    print(research2)
    
    pending_after = memory.get_pending_conversations()
    print(f"\nRemaining Pending at end: {len(pending_after)}")

if __name__ == '__main__':
    asyncio.run(run_tests())
