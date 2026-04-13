from agents.parser import parse_conversation
from agents.compressor import compress_conversation, compress_ai_response

raw = (
    "User: كيف أبني نظام Observer يراقب محادثات المستخدم مع الذكاء الاصطناعي دون أن يتدخل في وقت الاستجابة?\n\n"
    "Assistant: "
    "بناء نظام Observer غير متزامن يتطلب معمارية Event-Driven حيث يتم فصل طبقة المراقبة عن طبقة الاستجابة الفورية. "
    "الطريقة المثلى هي استخدام Queue (طابور مهام) مثل Redis Queue أو SQLite-backed queue. "
    "عند وصول رسالة من المستخدم يتم حفظها أولاً في قاعدة البيانات ثم يُرسل الطلب للنموذج اللغوي فوراً دون انتظار. "
    "في الخلفية، يقوم Worker مستقل بقراءة المحادثة من قاعدة البيانات وتحليلها بعد اكتمالها. "
    "هذا يضمن أن المستخدم لا يشعر بأي تأخير. يمكنك استخدام asyncio.create_task() في Python لتشغيل المهام الخلفية. "
    "احرص على إضافة timeout للمهام الخلفية حتى لا تتراكم. "
    "من أهم المخاطر: إذا مات الـServer أثناء معالجة Task، يجب أن يكون لديك Dead Letter Queue. "
    "استخدم Idempotent operations حتى لو أُعيد تشغيل المهمة لا تتكرر البيانات. "
    "النماذج المستخدمة للتحليل لا يجب أن تكون نفس النموذج المستخدم للإجابة — يمكن استخدام نموذج أرخص وأبطأ للتحليل. "
    "يجب مراعاة الـPrivacy: لا تحتفظ بمحادثات المستخدم أطول من اللازم في القاعدة. "
    * 4  # ~400+ words
)

print("=" * 60)
print("BEFORE COMPRESSION")
print("=" * 60)
words_before = len(raw.split())
print(f"Size: {words_before} words, {len(raw)} chars")
print()
print(raw[:600] + "...[truncated for display]")

print()
print("=" * 60)
print("AFTER COMPRESSION")
print("=" * 60)

parsed = parse_conversation(raw)
compressed = compress_conversation(parsed)
words_after = len(compressed.split())

print(f"Size: {words_after} words, {len(compressed)} chars")
reduction = (1 - words_after/words_before) * 100
print(f"Reduction: {reduction:.0f}%")
print()
print(compressed)
