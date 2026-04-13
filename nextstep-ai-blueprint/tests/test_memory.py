import pytest
import os
import database.db as db
import agents.memory as memory
from config import DB_PATH

@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    db.init_db()
    yield
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

def test_add_conversation():
    conv_id = memory.add_conversation("Test conv", "claude", "User: hello\nAssistant: hi")
    conv = memory.get_conversation(conv_id)
    assert conv["status"] == "pending"
    assert conv["word_count"] == 4
    assert conv["label"] == "Test conv"

def test_get_pending():
    memory.add_conversation("Conv 1", "claude", "...")
    memory.add_conversation("Conv 2", "gpt", "...")
    pending = memory.get_pending_conversations()
    assert len(pending) == 2
    assert pending[0]["status"] == "pending"

def test_mark_analyzed():
    conv_id = memory.add_conversation("Conv", "claude", "...")
    memory.mark_analyzed(conv_id)
    conv = memory.get_conversation(conv_id)
    assert conv["status"] == "analyzed"
