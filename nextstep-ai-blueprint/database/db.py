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
    _migrate(conn)
    conn.close()


def _migrate(conn):
    """Safe migrations — add columns/tables for existing databases."""
    # Add calibration_status column to insights if not exists
    cols = [r[1] for r in conn.execute("PRAGMA table_info(insights)").fetchall()]
    if "calibration_status" not in cols:
        conn.execute("ALTER TABLE insights ADD COLUMN calibration_status TEXT DEFAULT 'active'")
        conn.commit()

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
    import json
    conn = get_connection()
    cur = conn.execute("SELECT * FROM research_results WHERE report_id = ?", (report_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {}
    
    try:
        discoveries = json.loads(row["discoveries"]) if row["discoveries"] else []
    except Exception:
        discoveries = []
        
    try:
        queries = json.loads(row["search_queries"]) if row["search_queries"] else []
    except Exception:
        queries = []
        
    return {
        "discoveries": discoveries,
        "research_summary": row["research_summary"] or "",
        "search_queries_used": queries
    }


def upsert_map_input(map_type: str, input_type: str, content: str, source_url: str = None) -> str:
    import uuid
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM user_maps WHERE map_type = ? AND input_type = ? AND is_active = 1",
        (map_type, input_type)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE user_maps SET content = ?, source_url = ?, last_updated = ? WHERE id = ?",
            (content, source_url, now, existing["id"])
        )
        conn.commit()
        conn.close()
        return existing["id"]
    else:
        new_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO user_maps (id, map_type, input_type, content, source_url, added_at, last_updated, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
            (new_id, map_type, input_type, content, source_url, now, now)
        )
        conn.commit()
        conn.close()
        return new_id


def get_map_inputs(map_type: str) -> list:
    conn = get_connection()
    cur = conn.execute("SELECT * FROM user_maps WHERE map_type = ? AND is_active = 1 ORDER BY added_at", (map_type,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_all_active_maps() -> dict:
    result = {"cognitive": [], "behavioral": [], "personal": []}
    conn = get_connection()
    cur = conn.execute("SELECT * FROM user_maps WHERE is_active = 1 ORDER BY map_type, added_at")
    for row in cur.fetchall():
        r = dict(row)
        mt = r["map_type"]
        if mt in result:
            result[mt].append(r)
    conn.close()
    return result


def deactivate_map_input(map_id: str) -> None:
    conn = get_connection()
    conn.execute("UPDATE user_maps SET is_active = 0 WHERE id = ?", (map_id,))
    conn.commit()
    conn.close()


def insert_ensemble_result(ensemble_id, report_id, domains_identified, agent_count,
                           completion_findings, alignment_findings, contradiction_findings):
    import json
    from datetime import datetime, timezone
    conn = get_connection()
    timestamp = datetime.now(timezone.utc).isoformat()
    domains_json = json.dumps(domains_identified, ensure_ascii=False) if isinstance(domains_identified, list) else domains_identified
    completion_json = json.dumps(completion_findings, ensure_ascii=False) if isinstance(completion_findings, list) else completion_findings
    alignment_json = json.dumps(alignment_findings, ensure_ascii=False) if isinstance(alignment_findings, list) else alignment_findings
    contradiction_json = json.dumps(contradiction_findings, ensure_ascii=False) if isinstance(contradiction_findings, list) else contradiction_findings
    conn.execute(
        "INSERT INTO domain_ensemble_results (id, report_id, timestamp, domains_identified, agent_count, completion_findings, alignment_findings, contradiction_findings) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (ensemble_id, report_id, timestamp, domains_json, agent_count, completion_json, alignment_json, contradiction_json)
    )
    conn.commit()
    conn.close()
    return ensemble_id


def get_ensemble_by_report(report_id):
    import json
    conn = get_connection()
    cur = conn.execute("SELECT * FROM domain_ensemble_results WHERE report_id = ?", (report_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {}
        
    try:
        domains = json.loads(row["domains_identified"]) if row["domains_identified"] else []
    except Exception:
        domains = []
        
    try:
        completion = json.loads(row["completion_findings"]) if row["completion_findings"] else []
    except Exception:
        completion = []
        
    try:
        alignment = json.loads(row["alignment_findings"]) if row["alignment_findings"] else []
    except Exception:
        alignment = []
        
    try:
        contradiction = json.loads(row["contradiction_findings"]) if row["contradiction_findings"] else []
    except Exception:
        contradiction = []
        
    return {
        "domains_identified": domains,
        "agent_count": row["agent_count"],
        "completion_findings": completion,
        "alignment_findings": alignment,
        "contradiction_findings": contradiction
    }


def update_insight_calibration_status(insight_id: str, status: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE insights SET calibration_status = ? WHERE id = ?",
        (status, insight_id)
    )
    conn.commit()
    conn.close()


def insert_calibration_log(report_id: str, insights_reviewed: int,
                           insights_weakened: int, calibration_summary: str,
                           weakened_details, stale_map_inputs) -> str:
    import uuid
    import json
    from datetime import datetime, timezone
    conn = get_connection()
    cal_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    weakened_json = json.dumps(weakened_details, ensure_ascii=False) if isinstance(weakened_details, list) else weakened_details
    stale_json = json.dumps(stale_map_inputs, ensure_ascii=False) if isinstance(stale_map_inputs, list) else stale_map_inputs
    conn.execute(
        "INSERT INTO calibration_log (id, report_id, timestamp, insights_reviewed, insights_weakened, calibration_summary, weakened_details, stale_map_inputs) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (cal_id, report_id, timestamp, insights_reviewed, insights_weakened, calibration_summary, weakened_json, stale_json)
    )
    conn.commit()
    conn.close()
    return cal_id


def get_insights_for_calibration(limit: int = 30) -> list:
    conn = get_connection()
    cur = conn.execute(
        "SELECT * FROM insights WHERE calibration_status = 'active' ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_calibration_log(limit: int = 10) -> list:
    conn = get_connection()
    cur = conn.execute("SELECT * FROM calibration_log ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
