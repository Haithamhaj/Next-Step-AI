import os
import json
from openai import OpenAI
from config import OPENAI_API_KEY, INSIGHT_MODEL, PROMPTS_DIR

def load_prompt(filename: str) -> str:
    path = os.path.join(PROMPTS_DIR, filename)
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def analyze_conversations(conversations_block: str, profile: str, lang: str = "ar", discoveries: list = None, ensemble_output: dict = None) -> dict:
    if not OPENAI_API_KEY or "-key-" in OPENAI_API_KEY:
        pass 

    system_prompt_raw = load_prompt("insight_session_system.txt")
    system_prompt = system_prompt_raw.replace("{lang}", lang)
    user_prompt_template = load_prompt("insight_session_user.txt")
    
    user_prompt = user_prompt_template.replace("{conversations_block}", conversations_block)
    user_prompt = user_prompt.replace("{user_profile}", profile)

    # Inject discoveries block if provided
    discoveries = discoveries or []
    if discoveries:
        discoveries_lines = []
        for d in discoveries:
            title = d.get("title", "Unknown")
            dtype = d.get("type", "concept")
            relevance = d.get("relevance", "")
            suggested_angle = d.get("suggested_angle", "")
            source = d.get("source", "")
            line = f"- {title} ({dtype}): {relevance}"
            if suggested_angle:
                line += f" | Suggested angle: {suggested_angle}"
            if source:
                line += f" | Source: {source}"
            discoveries_lines.append(line)
        discoveries_block = "\n".join(discoveries_lines)
        user_prompt += f"\n\n## External Discoveries (Research Agent findings)\nThese are tools, standards, and concepts found outside the conversations that are directly relevant to the topic. Use these to generate ALIGNMENT findings — do not ignore them.\n\n{discoveries_block}\n"

    # Inject domain ensemble observations if provided
    if ensemble_output:
        completion = ensemble_output.get("completion_findings", [])
        alignment = ensemble_output.get("alignment_findings", [])
        contradiction = ensemble_output.get("contradiction_findings", [])

        completion_text = "\n".join(f"- {f}" for f in completion) if completion else "None identified"
        alignment_text = "\n".join(f"- {f}" for f in alignment) if alignment else "None identified"
        contradiction_text = "\n".join(f"- {f}" for f in contradiction) if contradiction else "None identified"

        user_prompt += (
            f"\n\n## Domain Specialist Observations\n"
            f"The following observations were made by domain specialists\n"
            f"before your analysis. Use them to inform your findings —\n"
            f"especially to validate or challenge what you find.\n"
            f"Do not simply repeat them. Use them as signals.\n\n"
            f"### Missing Elements (Completion specialists):\n{completion_text}\n\n"
            f"### Adjacent Elements (Alignment specialists):\n{alignment_text}\n\n"
            f"### Challenges (Contradiction specialists):\n{contradiction_text}\n"
        )
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    last_error = "unknown"
    
    for _ in range(2): 
        try:
            res = client.chat.completions.create(
                model=INSIGHT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_completion_tokens=4000,
                response_format={"type": "json_object"}
            )
            text = res.choices[0].message.content
            
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
