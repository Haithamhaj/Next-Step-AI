import sqlite3
import os
from config import DB_PATH

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

def insert_conversation(conv_id, label, source, content, comp_content, added_at, word_count, comp_word_count, status="pending"):
    conn = get_connection()
    conn.execute(
        "INSERT INTO conversations (id, label, source, content, compressed_content, added_at, word_count, compressed_word_count, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (conv_id, label, source, content, comp_content, added_at, word_count, comp_word_count, status)
    )
    conn.commit()
    conn.close()

def update_conversation_status(conv_id, status, analyzed_at=None):
    conn = get_connection()
    if analyzed_at:
        conn.execute("UPDATE conversations SET status = ?, analyzed_at = ? WHERE id = ?", (status, analyzed_at, conv_id))
    else:
        conn.execute("UPDATE conversations SET status = ? WHERE id = ?", (status, conv_id))
    conn.commit()
    conn.close()

def get_pending_conversations():
    conn = get_connection()
    cur = conn.execute("SELECT * FROM conversations WHERE status = 'pending' ORDER BY added_at ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_conversation(conv_id):
    conn = get_connection()
    cur = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_conversations():
    conn = get_connection()
    cur = conn.execute("SELECT * FROM conversations ORDER BY added_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def delete_conversation(conv_id):
    conn = get_connection()
    conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    conn.commit()
    conn.close()

def insert_canonical(u_id, conversation_id, timestamp, unit_type, summary, content, topic_tags):
    conn = get_connection()
    import json
    tags_json = json.dumps(topic_tags, ensure_ascii=False) if isinstance(topic_tags, list) else topic_tags
    conn.execute(
        "INSERT INTO canonical_units (id, conversation_id, timestamp, unit_type, summary, content, topic_tags) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (u_id, conversation_id, timestamp, unit_type, summary, content, tags_json)
    )
    conn.commit()
    conn.close()

def insert_insight(i_id, report_id, timestamp, insight_type, content, evidence, impact, convs_ref, conversation_ids=None, missing_angle=None, why_it_matters=None, ready_prompt=None, confidence=None, confidence_reason=None, profile_connection=None):
    conn = get_connection()
    import json
    convs_json = json.dumps(convs_ref, ensure_ascii=False) if isinstance(convs_ref, list) else convs_ref
    # Store all analyzed conversation IDs as a JSON array in conversation_id
    conv_id_json = json.dumps(conversation_ids, ensure_ascii=False) if isinstance(conversation_ids, list) else conversation_ids
    conn.execute(
        "INSERT INTO insights (id, report_id, conversation_id, timestamp, insight_type, content, evidence, impact, conversations_referenced, missing_angle, why_it_matters, ready_prompt, confidence, confidence_reason, profile_connection) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (i_id, report_id, conv_id_json, timestamp, insight_type, content, evidence, impact, convs_json, missing_angle, why_it_matters, ready_prompt, confidence, confidence_reason, profile_connection)
    )
    conn.commit()
    conn.close()

def get_all_insights():
    conn = get_connection()
    cur = conn.execute("SELECT * FROM insights ORDER BY timestamp DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def rate_insight(insight_id, score):
    conn = get_connection()
    conn.execute("UPDATE insights SET quality_score = ? WHERE id = ?", (score, insight_id))
    conn.commit()
    conn.close()

def insert_report(r_id, date, timestamp, report_content, insights_count, sessions_count):
    conn = get_connection()
    conn.execute(
        "INSERT INTO daily_reports (id, date, timestamp, report_content, insights_count, sessions_count) VALUES (?, ?, ?, ?, ?, ?)",
        (r_id, date, timestamp, report_content, insights_count, sessions_count)
    )
    conn.commit()
    conn.close()

def insert_contextual_instruction(instruction_id, report_id, content, topic_summary, lang):
    conn = get_connection()
    timestamp = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO contextual_instructions (id, report_id, timestamp, content, topic_summary, lang) VALUES (?, ?, ?, ?, ?, ?)",
        (instruction_id, report_id, timestamp, content, topic_summary, lang)
    )
    conn.commit()
    conn.close()
    return instruction_id

def get_contextual_instructions(limit=10):
    conn = get_connection()
    cur = conn.execute("SELECT * FROM contextual_instructions ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_instruction_by_report(report_id):
    conn = get_connection()
    cur = conn.execute("SELECT * FROM contextual_instructions WHERE report_id = ?", (report_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def insert_research_result(research_id, report_id, topic_summary, discoveries, search_queries, research_summary):
    import json
    conn = get_connection()
    timestamp = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
    discoveries_json = json.dumps(discoveries, ensure_ascii=False) if isinstance(discoveries, list) else discoveries
    queries_json = json.dumps(search_queries, ensure_ascii=False) if isinstance(search_queries, list) else search_queries
    conn.execute(
        "INSERT INTO research_results (id, report_id, timestamp, topic_summary, discoveries, search_queries, research_summary) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (research_id, report_id, timestamp, topic_summary, discoveries_json, queries_json, research_summary)
    )
    conn.commit()
    conn.close()
    return research_id

def get_research_by_report(report_id):
    conn = get_connection()
    cur = conn.execute("SELECT * FROM research_results WHERE report_id = ?", (report_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None
