# RepoLens AI — Architecture Decision Record Log

هذا الملف يسجل القرارات الهندسية الجوهرية التي تؤثر على المشروع.

لا يتم تسجيل كل قرار صغير؛ فقط القرارات التي تؤثر على Architecture أو Security أو extensibility أو development workflow.

---

## ADR-001 — Modular Monolith

**Status:** Accepted

### القرار

سيُبنى RepoLens AI كـModular Monolith في MVP.

### السبب

نحتاج إلى حدود داخلية واضحة مع أقل Operational Complexity ممكن.

Microservices ليست مطلوبة للـMVP.

---

## ADR-002 — GitHub as Primary Repository Source

**Status:** Accepted

### القرار

GitHub Repository URL هو مصدر الإدخال الرئيسي في MVP.

### السبب

هذا هو الـCore User Journey للمشروع، كما أنه يجعل Demo النهائي واضحًا:

```text
GitHub URL
→ Analysis
→ Report
```

Repository Source abstraction ستسمح بإضافة Local أو GitLab لاحقًا.

---

## ADR-003 — Evidence First, AI Assisted

**Status:** Accepted

### القرار

Deterministic Analysis هو مصدر Facts وMetrics.

AI مسؤول عن Interpretation وCorrelation وExplanation وRecommendations.

### السبب

لمنع hallucinated metrics والنتائج غير القابلة للتحقق.

---

## ADR-004 — No Automatic Arbitrary Repository Execution

**Status:** Accepted

### القرار

لن يتم تشغيل scripts أو install commands أو arbitrary repository code تلقائيًا.

### السبب

GitHub repositories external input غير موثوق.

Static analysis هو default.

---

## ADR-005 — Provider-Agnostic AI

**Status:** Accepted

### القرار

سيتم عزل AI provider خلف `AIProvider` abstraction.

### السبب

تقليل vendor lock-in وتسهيل الاختبار والاستبدال.

---

## ADR-006 — Report Generation as Separate Layer

**Status:** Accepted

### القرار

Report generation منفصل عن analysis.

### السبب

السماح بوجود HTML وJSON وMarkdown دون تكرار منطق التحليل.

---

## ADR-007 — Human Executes Git Write Operations by Default

**Status:** Accepted

### القرار

الـAgent يقترح أوامر Git، بينما المستخدم ينفذ `add/commit/push/merge/release` بنفسه ما لم يُطلب خلاف ذلك صراحة.

### السبب

- Human-in-the-loop
- قابلية توثيق أفضل
- screenshots
- سيطرة المستخدم على Git history

---

## ADR-008 — Windows-First Developer Experience

**Status:** Accepted

### القرار

الـdevelopment scripts الأساسية ستكون PowerShell.

### السبب

بيئة التطوير الفعلية للمشروع هي Windows.

---

## ADR-009 — MVP Scope Control

**Status:** Accepted

### القرار

الأولوية هي إنجاز end-to-end vertical slice يعمل فعليًا بدل بناء عشرات الميزات غير المكتملة.

### السبب

الـMVP يحتاج إلى demonstration قابلة للتشغيل والشرح.

---

## ADR-010 — Multi-provider AI Architecture

**Status:** Accepted

### القرار

دعم أكثر من مزود للذكاء الاصطناعي (مثل Google و OpenRouter) باستخدام `AIProvider` Protocol موحد. يتم اختيار المزود صراحة عبر متغير البيئة `REPOLENS_AI_PROVIDER`.

### السبب

منع vendor lock-in، وتوفير مرونة للمستخدم في اختيار نموذج أو مزود مختلف (مثل OpenRouter)، مع الحفاظ على التوافقية مع المزود الافتراضي (Google). لا يتم استخدام التبديل التلقائي (silent fallback) عند فشل المزود للحفاظ على حتمية وسهولة التنقيح (debuggability).
