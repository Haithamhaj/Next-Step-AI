"""
cleaner.py — Strip low-signal content from conversation text before compression.

Removes:
  - Fenced code blocks (``` ... ```)
  - Inline backtick code longer than 60 chars
  - JSON / XML / HTML blobs
  - Long numbered/bulleted lists that are purely technical (imports, file paths, env vars)
  - Base64 / hex strings
  - Repeated separator lines (===, ---, ***)
  - Stack traces and error logs
  - File diffs

Keeps:
  - All user messages (never altered)
  - Prose sentences and reasoning in AI responses
  - Questions, decisions, recommendations
  - Short code references (variable names, function names)
"""

import re

# ── Patterns to strip from AI response text ──────────────────

# Fenced code blocks: ```...``` (multi-line)
_CODE_BLOCK = re.compile(r'```[\s\S]*?```', re.MULTILINE)

# Inline code longer than 60 chars: `some long thing`
_LONG_INLINE = re.compile(r'`[^`]{60,}`')

# JSON-like blobs: lines that are mostly { } [ ] : " symbols
_JSON_LINE = re.compile(r'^[\s\{\}\[\]"\',:0-9\.\-_]{20,}$', re.MULTILINE)

# XML/HTML tags
_HTML_TAGS = re.compile(r'<[^>]{3,}>')

# Base64 or hex strings (20+ chars of [A-Za-z0-9+/=])
_BASE64 = re.compile(r'[A-Za-z0-9+/=]{40,}')

# Stack traces: lines starting with "at ", "File ", "Traceback"
_STACK = re.compile(r'^(Traceback.*|.*File ".*", line \d+.*|.*at .*\(.*:\d+:\d+\).*)$', re.MULTILINE)

# Long separator lines: ===, ---, ***, ___
_SEPARATOR = re.compile(r'^[=\-\*_]{4,}$', re.MULTILINE)

# Long file paths / import lines
_FILE_PATH = re.compile(r'(/[\w\./\-_]{15,}|\\[\w\\\.\-_]{15,})', re.MULTILINE)

# Diff lines (+++ --- @@ lines)
_DIFF = re.compile(r'^(\+\+\+|---|@@|diff --git).*$', re.MULTILINE)

# Long numeric sequences (IDs, hashes)
_HASH = re.compile(r'\b[a-f0-9]{16,}\b')

# Lines that are pure punctuation / symbols
_SYMBOL_LINE = re.compile(r'^[^\w\u0600-\u06FF]{5,}$', re.MULTILINE)


def clean_ai_response(text: str) -> str:
    """Remove low-signal content from a single AI response."""
    # Order matters: strip largest blocks first
    text = _CODE_BLOCK.sub('[CODE BLOCK REMOVED]', text)
    text = _DIFF.sub('', text)
    text = _STACK.sub('', text)
    text = _HTML_TAGS.sub('', text)
    text = _BASE64.sub('[HASH/BASE64]', text)
    text = _HASH.sub('[HASH]', text)
    text = _LONG_INLINE.sub('[code]', text)
    text = _JSON_LINE.sub('', text)
    text = _FILE_PATH.sub('[path]', text)
    text = _SEPARATOR.sub('', text)
    text = _SYMBOL_LINE.sub('', text)

    # Collapse 3+ blank lines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def clean_conversation(parsed_messages: list) -> list:
    """
    Clean an already-parsed conversation.
    User messages: NEVER altered.
    Assistant messages: stripped of low-signal content.

    Returns cleaned list of {role, content} dicts.
    """
    cleaned = []
    for msg in parsed_messages:
        if msg['role'] == 'user':
            cleaned.append(msg)          # Keep 100% as-is
        else:
            clean_text = clean_ai_response(msg['content'])
            # If the response became mostly empty after cleaning, replace with a note
            if len(clean_text.split()) < 5:
                clean_text = '[AI response was primarily code/technical output — no prose to analyze]'
            cleaned.append({'role': msg['role'], 'content': clean_text})
    return cleaned


def estimate_code_ratio(text: str) -> float:
    """
    Returns 0.0-1.0: fraction of the text that is code/technical.
    Useful for showing a badge in the UI.
    """
    total_lines = max(len(text.splitlines()), 1)
    code_lines = len(_CODE_BLOCK.findall(text)) * 10  # rough estimate
    code_lines += len([l for l in text.splitlines()
                       if re.match(r'^\s{4,}\S', l)])  # indented code
    return min(code_lines / total_lines, 1.0)
