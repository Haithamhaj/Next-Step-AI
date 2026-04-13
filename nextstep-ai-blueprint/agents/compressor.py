import anthropic
from config import ANTHROPIC_API_KEY

COMPRESSOR_MODEL = "claude-3-haiku-20240307"

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
    # Compress responses with more than 30 words (lowered from 100 to handle many short-ish responses)
    if len(response_text.split()) < 30:
        return response_text
        
    if not ANTHROPIC_API_KEY or "-key-" in ANTHROPIC_API_KEY:
        return response_text
        
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    try:
        result = client.messages.create(
            model=COMPRESSOR_MODEL,
            max_tokens=300,
            temperature=0,
            system=COMPRESSOR_PROMPT,
            messages=[{"role": "user", "content": response_text}]
        )
        return result.content[0].text
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
