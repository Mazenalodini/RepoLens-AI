# RepoLens AI — Agent Control Kit

هذا المجلد يحتوي على الوثائق والتعليمات التي تحكم استخدام AI Agents أثناء تطوير RepoLens AI.

## طريقة الاستخدام

انسخ محتويات هذه الحزمة إلى جذر مشروع RepoLens-AI مع الحفاظ على البنية.

البنية:

```text
AGENTS.md
docs/
instructions/
agents/
prompts/
```

## الترتيب

1. اقرأ `docs/PROJECT_SPEC.md`.
2. اقرأ `docs/ARCHITECTURE.md`.
3. راجع `docs/DECISIONS.md`.
4. استخدم `AGENTS.md` كـAgent Operating System.
5. استخدم ملفات `instructions/` حسب المهمة.
6. استخدم `prompts/BOOTSTRAP_PROMPT.md` لمرحلة الفحص الأولي.
7. استخدم `prompts/MASTER_PROMPT.md` لتأسيس طريقة العمل طويلة المدى.
8. استخدم `prompts/TASK_PROMPT_TEMPLATE.md` لإنشاء مهام صغيرة وواضحة.

## قاعدة مهمة

لا تعطِ Agent أمرًا من نوع:

> "Build the whole project."

قسّم العمل إلى Vertical Slices وBounded Tasks.

## Human-in-the-Loop

الـAgent مسؤول عن:

```text
Plan
Implement
Test
Review
Report
```

والمستخدم مسؤول افتراضيًا عن:

```text
Git Write Operations
Commit
Push
Merge
Release
```

هذا يسمح أيضًا بتوثيق مراحل المشروع ولقطات الشاشة بوضوح.
