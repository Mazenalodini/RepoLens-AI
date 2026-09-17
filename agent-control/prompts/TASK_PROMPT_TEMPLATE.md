# RepoLens AI — Bounded Task Prompt Template

استخدم هذا القالب لكل Task جديدة في Antigravity.

```text
المهمة:

أريد تنفيذ Task محددة داخل RepoLens AI.

قبل التنفيذ:

1. اقرأ AGENTS.md.
2. اقرأ الوثائق ذات العلاقة.
3. افحص الملفات الحالية المرتبطة بالمهمة.
4. لا تغير Architecture من تلقاء نفسك.
5. لا تنفذ أي جزء خارج Scope المهمة.

السياق:

<اكتب هنا لماذا نحتاج هذه المهمة>

المطلوب:

<اكتب المطلوب بدقة>

القيود:

- الالتزام بالـArchitecture الحالية.
- استخدام Type Hints.
- الحفاظ على Separation of Concerns.
- عدم إضافة Dependencies بلا حاجة.
- كتابة Tests مناسبة.
- عدم إجراء Git commit أو push تلقائيًا.
- عدم تشغيل arbitrary repository code.

Acceptance Criteria:

1. ...
2. ...
3. ...

طريقة العمل:

READ
→ UNDERSTAND
→ PLAN
→ IMPLEMENT
→ TEST
→ DIFF REVIEW
→ REPORT
→ STOP

بعد الانتهاء أعطني:

- Status
- Files Created
- Files Modified
- Implementation Summary
- Tests Executed + Actual Results
- Diff Review
- Limitations
- Out of Scope
- Manual Terminal Commands
- Git Checkpoint
- Screenshot Checkpoint
- Next Task
```
