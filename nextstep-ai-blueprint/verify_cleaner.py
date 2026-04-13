"""Quick verification: show before/after cleaning on the problematic conversation."""
import sys
sys.path.insert(0, '.')

import database.db as db
from agents.parser import parse_conversation
from agents.cleaner import clean_conversation, estimate_code_ratio
from agents.compressor import compress_conversation

conn = db.get_connection()
conv = conn.execute(
    "SELECT label, content, word_count, compressed_word_count FROM conversations WHERE label LIKE '%Claude%'"
).fetchone()
conn.close()

if not conv:
    print("Conversation not found")
    exit()

c = dict(conv)
print(f"Label: {c['label']}")
print(f"Original: {c['word_count']} words")
print(f"Old compressed: {c['compressed_word_count']} words")
print()

# Estimate code ratio
ratio = estimate_code_ratio(c['content'])
print(f"Code/technical ratio: {ratio*100:.0f}%")
print()

# New pipeline: parse → clean → compress
parsed  = parse_conversation(c['content'])
cleaned = clean_conversation(parsed)
new_compressed = compress_conversation(cleaned)

# Count sizes at each stage
orig_chars = len(c['content'])
after_clean_chars = sum(len(m['content']) for m in cleaned)
after_compress_chars = len(new_compressed)

print(f"Pipeline results:")
print(f"  Original:    {orig_chars:>8,} chars  ({c['word_count']:>6,} words)")
print(f"  After clean: {after_clean_chars:>8,} chars  ({len(' '.join(m['content'] for m in cleaned).split()):>6,} words)  ← {(1 - after_clean_chars/orig_chars)*100:.0f}% removed")
print(f"  After compress: {after_compress_chars:>5,} chars  ({len(new_compressed.split()):>6,} words)  ← {(1 - after_compress_chars/orig_chars)*100:.0f}% total reduction")
print()
print(f"Will fit in 20k hard cap? {'✅ YES' if after_compress_chars <= 20000 else f'⚠️ NO — still {after_compress_chars - 20000:,} chars over'}")
print()
print("── First 800 chars of cleaned+compressed output ──")
print(new_compressed[:800])
