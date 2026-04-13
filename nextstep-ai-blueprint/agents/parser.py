import re

def parse_conversation(raw_text: str) -> list:
    pattern = r'^(?:##\s*)?(User|Human|المستخدم|ChatGPT|Claude|Assistant|AI|المساعد)\s*[:\n]?'
    
    messages = []
    current_role = "user"
    current_content = []
    
    lines = raw_text.split('\n')
    has_structure = False
    
    for line in lines:
        match = re.search(pattern, line, flags=re.IGNORECASE)
        if match:
            has_structure = True
            if current_content:
                messages.append({"role": current_role, "content": "\n".join(current_content).strip()})
                current_content = []
                
            speaker = match.group(1).lower()
            if speaker in ["user", "human", "المستخدم"]:
                current_role = "user"
            else:
                current_role = "assistant"
                
            rest_of_line = re.sub(pattern, '', line, flags=re.IGNORECASE).strip()
            if rest_of_line:
                current_content.append(rest_of_line)
        else:
            current_content.append(line)
            
    if current_content:
        messages.append({"role": current_role, "content": "\n".join(current_content).strip()})
        
    if not has_structure:
        return [{"role": "user", "content": raw_text}]
        
    return [m for m in messages if m["content"].strip()]
