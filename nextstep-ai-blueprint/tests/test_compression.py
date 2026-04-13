import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.parser import parse_conversation
from agents.compressor import compress_ai_response, compress_conversation
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


# ─────────────────────────────────────────────────────────────
# TEST 1 — Short response: no compression API call needed
# ─────────────────────────────────────────────────────────────
def test_short_response_no_compression():
    short = "The answer is 42."
    result = compress_ai_response(short)
    assert result == short, "Short responses must be returned as-is"

# ─────────────────────────────────────────────────────────────
# TEST 2 — Long response: should produce 4-element structure
# ─────────────────────────────────────────────────────────────
def test_long_response_gets_compressed():
    long_response = (
        "Retrieval-Augmented Generation (RAG) works by combining a retrieval step "
        "with a generation step. First, the system retrieves relevant documents from "
        "a vector database using semantic similarity search. The retrieved chunks are "
        "then included in the prompt sent to the language model. This allows the model "
        "to ground its responses in up-to-date, factual information from your own data. "
        "Key trade-offs include: latency increases due to the retrieval step, you need "
        "to maintain a vector index, and chunking strategy significantly affects quality. "
        "Common pitfalls are overlapping chunks, poor embedding models, and not tuning "
        "the similarity threshold. You should evaluate RAG quality using metrics like "
        "faithfulness, context precision, and context recall. Tools like Ragas or LangSmith "
        "can help with evaluation. The retrieval component is often the bottleneck in "
        "production systems, so caching frequently retrieved chunks is recommended."
    ) * 2  # ~200+ words

    result = compress_ai_response(long_response)
    assert len(result.split()) < len(long_response.split()), "Should be shorter"
    assert "Covered:" in result or "covered" in result.lower(), "Must have Covered element"

# ─────────────────────────────────────────────────────────────
# TEST 3 — Full conversation compression: user messages intact
# ─────────────────────────────────────────────────────────────
def test_user_messages_preserved():
    raw = (
        "User: How does RAG work?\n"
        "Assistant: " + ("RAG retrieves documents then generates answers. " * 30) + "\n"
        "User: What about latency?\n"
        "Assistant: " + ("Latency comes from the retrieval step which adds 200-500ms. " * 30)
    )
    parsed = parse_conversation(raw)
    compressed = compress_conversation(parsed)

    assert "How does RAG work?" in compressed, "User message 1 must be intact"
    assert "What about latency?" in compressed, "User message 2 must be intact"
    assert "[AI RESPONSE SUMMARY]" in compressed, "AI responses must be compressed"
    assert "[USER]" in compressed, "User blocks must be labelled"

# ─────────────────────────────────────────────────────────────
# TEST 4 — Compression ratio stored in DB
# ─────────────────────────────────────────────────────────────
def test_compression_ratio_in_db():
    raw = (
        "User: Tell me about Temporal Knowledge Graphs?\n"
        "Assistant: " + ("A temporal knowledge graph stores time-stamped facts about entities. " * 60)
    )
    conv_id = memory.add_conversation("Ratio Test", "Claude", raw)
    conv = db.get_conversation(conv_id)

    orig = conv["word_count"]
    comp = conv["compressed_word_count"]
    ratio = comp / orig if orig > 0 else 1

    print(f"\n  Original:   {orig} words")
    print(f"  Compressed: {comp} words")
    print(f"  Ratio:      {ratio:.0%} of original ({(1-ratio)*100:.0f}% reduction)")

    assert comp is not None, "compressed_word_count must be stored"
    assert ratio < 0.9, "Should achieve at least 10% reduction on this synthetic test"

# ─────────────────────────────────────────────────────────────
# TEST 5 — Arabic conversation parsing
# ─────────────────────────────────────────────────────────────
def test_arabic_conversation_parsing():
    arabic_conv = (
        "المستخدم: كيف أبني أداة كوتشينج بالذكاء الاصطناعي؟\n"
        "المساعد: " + ("يمكنك بناء أداة كوتشينج باستخدام نماذج اللغة الكبيرة مع قاعدة بيانات للتتبع. " * 5)
    )
    parsed = parse_conversation(arabic_conv)
    assert len(parsed) >= 2, "Should parse at least 2 messages"
    assert parsed[0]["role"] == "user", "First message should be user"
    assert parsed[1]["role"] == "assistant" , "Second message should be assistant"
    assert "كوتشينج" in parsed[0]["content"], "Arabic user message should be preserved"

# ─────────────────────────────────────────────────────────────
# TEST 6 — Unstructured text treated as single user message
# ─────────────────────────────────────────────────────────────
def test_unstructured_text_fallback():
    plain = "هذا نص بدون تنسيق محادثة واضح"
    parsed = parse_conversation(plain)
    assert len(parsed) == 1
    assert parsed[0]["role"] == "user"
    assert plain in parsed[0]["content"]
