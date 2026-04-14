import os
from openai import OpenAI
from config import OPENAI_API_KEY, COMPRESSOR_MODEL

COMPRESSOR_PROMPT = """Extract exactly 4 elements from this AI response. Be concise — max 2 lines each.

1. COVERED: What main topics/points did the response address?
2. RECOMMENDED: What specific decisions, actions, or conclusions did it suggest?
3. WARNED: What risks, limitations, or caveats did it mention?
4. UNKNOWN: What did it explicitly say it doesn't know or is uncertain about?

If an element is empty, write "None mentioned."

Format:
- Covered: ...
- Recommended: ...
- Warned: ...
- Unknown: ...

Respond in the same language as the input. Be extremely concise."""

def compress_ai_response(response_text: str) -> str:
    # Compress responses with more than 30 words
    if len(response_text.split()) < 30:
        return response_text
        
    if not OPENAI_API_KEY or "-key-" in OPENAI_API_KEY:
        return response_text
        
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        res = client.chat.completions.create(
            model=COMPRESSOR_MODEL,
            messages=[
                {"role": "system", "content": COMPRESSOR_PROMPT},
                {"role": "user", "content": response_text}
            ],
            max_completion_tokens=300,
            temperature=0
        )
        return res.choices[0].message.content
    except Exception as e:
        print(f"Compression failed: {e}")
        return response_text

def compress_conversation(parsed_messages: list) -> str:
    compressed_parts = []
    
    for msg in parsed_messages:
        if msg["role"] == "user":
            compressed_parts.append(f"[USER]: {msg['content']}")
        elif msg["role"] == "assistant":
            summary = compress_ai_response(msg["content"])
            compressed_parts.append(f"[AI RESPONSE SUMMARY]:\n{summary}")
            
    return "\n\n".join(compressed_parts)
