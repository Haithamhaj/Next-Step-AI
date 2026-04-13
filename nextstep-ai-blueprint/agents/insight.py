import os
import json
import anthropic
from config import ANTHROPIC_API_KEY, INSIGHT_MODEL, PROMPTS_DIR

def load_prompt(filename: str) -> str:
    path = os.path.join(PROMPTS_DIR, filename)
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def analyze_conversations(conversations_block: str, profile: str, lang: str = "ar") -> dict:
    if not ANTHROPIC_API_KEY or "-key-" in ANTHROPIC_API_KEY:
        pass 

    system_prompt_raw = load_prompt("insight_session_system.txt")
    system_prompt = system_prompt_raw.replace("{lang}", lang)
    user_prompt_template = load_prompt("insight_session_user.txt")
    
    user_prompt = user_prompt_template.replace("{conversations_block}", conversations_block)
    user_prompt = user_prompt.replace("{user_profile}", profile)
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    last_error = "unknown"
    
    for _ in range(2): 
        try:
            res = client.messages.create(
                model=INSIGHT_MODEL,
                max_tokens=4000,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            text = res.content[0].text
            
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
                
            data = json.loads(text.strip())
            
            if "has_insight" not in data or "findings" not in data:
                raise ValueError("Invalid structure")
            return data
            
        except Exception as e:
            last_error = str(e)
            continue
            
    return {
        "has_insight": False, 
        "session_summary": f"تحليل فاشل بسبب خطأ تقني.", 
        "findings": [], 
        "skip_reason": f"API error: {last_error}", 
        "error": True
    }
