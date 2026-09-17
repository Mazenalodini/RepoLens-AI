# RepoLens AI — Bootstrap Prompt

استخدم هذا الـPrompt بعد أن تكون ملفات التحكم قد وُضعت في Workspace وقبل بدء تنفيذ Features.

```text
أنت الآن تعمل داخل Workspace لمشروع RepoLens AI.

لا تبدأ البرمجة.

نفّذ مرحلة Bootstrap & Repository Assessment فقط.

أولًا اقرأ:

AGENTS.md
docs/PROJECT_SPEC.md
docs/ARCHITECTURE.md
docs/DECISIONS.md
docs/ROADMAP.md
docs/DEVELOPMENT_WORKFLOW.md

ثم افحص Workspace الحالية.

المطلوب منك:

1. التأكد من بنية الملفات الحالية.
2. تحديد ما هو موجود وما هو مفقود.
3. عدم إنشاء Features.
4. عدم إضافة Dependencies غير مطلوبة.
5. عدم تعديل Architecture.
6. اقتراح Project Foundation المطلوبة للـMVP.
7. إنشاء خطة تنفيذ قصيرة مرتبة حسب الأولوية.

لا تنفذ Git commits أو push.

في نهاية الرد استخدم:

BOOTSTRAP STATUS
PROJECT UNDERSTANDING
CURRENT WORKSPACE
ARCHITECTURE UNDERSTANDING
MISSING FOUNDATION
RISKS
PROPOSED PHASE 1
MANUAL TERMINAL COMMANDS
SCREENSHOT CHECKPOINT

ثم توقف وانتظر المهمة التالية.
```
