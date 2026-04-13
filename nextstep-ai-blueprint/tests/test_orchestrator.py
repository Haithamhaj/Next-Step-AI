import pytest
import asyncio
import os
import database.db as db
import agents.memory as memory
import orchestrator
from unittest.mock import patch
from config import DB_PATH

@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    db.init_db()
    yield
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

@pytest.mark.asyncio
async def test_analyze_flow():
    memory.add_conversation("Test", "claude", "User: How does RAG work?\nAssistant: RAG is...")
    
    with patch("agents.insight.analyze_conversations") as mock_insight:
        mock_insight.return_value = {
            "has_insight": True,
            "session_summary": "Testing RAG",
            "angles": [{"type":"informational", "content":"missing context", "evidence":"none", "impact":"low", "conversations_referenced": []}],
            "ready_questions": ["What next?"]
        }
        with patch("agents.synthesis.generate_report") as mock_synthesis:
            mock_synthesis.return_value = "# Report\nنتائج"
            with patch("agents.synthesis.generate_contextual_instructions") as mock_ci:
                mock_ci.return_value = "You are an expert. Be specific."

                result = await orchestrator.analyze_and_report()
                report = result[0]
                contextual_instructions = result[1]

                assert report is not None
                assert "نتائج" in report or "findings" in report.lower()
                assert contextual_instructions is not None
            
            pending = memory.get_pending_conversations()
            assert len(pending) == 0
