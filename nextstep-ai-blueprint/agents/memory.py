import uuid
from datetime import datetime, timezone
import database.db as db

def extract_topic_tags(text: str) -> list:
    topic_keywords = {
        "coaching": ["coaching", "كوتشينج", "icf", "competency"],
        "architecture": ["architecture", "معمارية", "system design", "agent"],
        "business": ["budget", "ميزانية", "pricing", "revenue", "cost"],
        "ai": ["model", "llm", "prompt", "rag", "fine-tuning"],
        "product": ["mvp", "feature", "user", "ux", "onboarding"],
        "database": ["database", "sqlite", "postgres", "sql"],
        "performance": ["performance", "أداء"],
        "latency": ["latency", "بطء"]
    }
    
    text_lower = text.lower()
    tags = []
    for tag, keywords in topic_keywords.items():
        if any(kw.lower() in text_lower for kw in keywords):
            tags.append(tag)
    
    return tags if tags else ["general"]

def add_conversation(label: str, source: str, content: str) -> str:
    from agents.parser import parse_conversation
    from agents.cleaner import clean_conversation, estimate_code_ratio
    from agents.compressor import compress_conversation
    
    # 1. Parse into messages
    parsed = parse_conversation(content)
    
    # 2. Clean: remove code blocks, stack traces, etc. from AI responses
    cleaned = clean_conversation(parsed)
    
    # 3. Compress: summarise AI responses into 4-element structure
    compressed = compress_conversation(cleaned)
    
    conv_id = str(uuid.uuid4())
    added_at = datetime.now(timezone.utc).isoformat()
    word_count = len(content.split())
    comp_word_count = len(compressed.split())
    
    db.insert_conversation(conv_id, label, source, content, compressed, added_at, word_count, comp_word_count)
    return conv_id

def get_pending_conversations():
    return db.get_pending_conversations()

def get_conversation(conv_id):
    return db.get_conversation(conv_id)

def mark_analyzed(conv_id: str):
    analyzed_at = datetime.now(timezone.utc).isoformat()
    db.update_conversation_status(conv_id, "analyzed", analyzed_at)

def build_context_block(conversations: list) -> str:
    block = ""
    for c in conversations:
        comp = c.get('compressed_content')
        text = comp if comp else c['content']
        block += f"=== Conversation: {c['label']} (Source: {c['source']}) ===\n"
        block += f"{text}\n\n"
    return block

def store_insight(insight_data: dict, report_id: str, conversation_ids: list = None) -> str:
    """Store a single insight. conversation_ids is the list of conv IDs analyzed together."""
    i_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    refs = insight_data.get("conversations_referenced", [])

    # Store 'missing_angle' in 'content' as well for backward compatibility
    content = insight_data.get("missing_angle", insight_data.get("content", ""))

    db.insert_insight(
        i_id,
        report_id,
        timestamp,
        insight_data.get("type", "informational"),
        content,
        insight_data.get("evidence", ""),
        insight_data.get("impact", "medium"),
        refs,
        conversation_ids=conversation_ids or [],
        missing_angle=insight_data.get("missing_angle", ""),
        why_it_matters=insight_data.get("why_it_matters", ""),
        ready_prompt=insight_data.get("ready_prompt", ""),
        confidence=insight_data.get("confidence", "moderate"),
        confidence_reason=insight_data.get("confidence_reason", ""),
        profile_connection=insight_data.get("profile_connection", "")
    )
    return i_id

def store_report(date: str, content: str, stats: dict) -> str:
    timestamp = datetime.now(timezone.utc).isoformat()
    r_id = str(uuid.uuid4())
    db.insert_report(r_id, date, timestamp, content,
                     stats.get("insights_count", 0),
                     stats.get("sessions_count", 0))
    return r_id
