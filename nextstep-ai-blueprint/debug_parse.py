import asyncio
from agents.insight import analyze_conversations
import database.db as db

conn = db.get_connection()
pending = conn.execute('SELECT label, source, content, compressed_content FROM conversations WHERE status=\'pending\'').fetchall()
conn.close()

c = dict(pending[0])
text_for_analysis = c.get('compressed_content') or c['content']
if len(text_for_analysis) > 20000:
    text_for_analysis = text_for_analysis[:20000]

from agents.memory import build_context_block
context_block = build_context_block([{'label': c['label'], 'source': c['source'], 'content': text_for_analysis}])

import anthropic
from config import ANTHROPIC_API_KEY, INSIGHT_MODEL
from agents.insight import load_prompt
system_prompt_raw = load_prompt('insight_session_system.txt')
system_prompt = system_prompt_raw.replace('{lang}', 'ar')
user_prompt_template = load_prompt('insight_session_user.txt')
user_prompt = user_prompt_template.replace('{conversations_block}', context_block).replace('{user_profile}', 'No profile')

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
res = client.messages.create(
    model=INSIGHT_MODEL,
    max_tokens=3000,
    temperature=0.3,
    system=system_prompt,
    messages=[{'role': 'user', 'content': user_prompt}]
)
text = res.content[0].text
print("--- RAW OUTPUT FROM ANTHROPIC ---")
print(text)
print("--- END RAW OUTPUT ---")

if '```json' in text:
    text = text.split('```json')[1].split('```')[0]
elif '```' in text:
    text = text.split('```')[1].split('```')[0]

import json
try:
    data = json.loads(text.strip())
    print("SUCCESSFUL PARSE!")
except Exception as e:
    print("JSON PARSE ERROR:", e)
