---
description: Run a task with one selected OpenRouter model throughout the lifecycle
agent: single-model
---

Use the single-model-lifecycle skill. This primary agent intentionally has no model override, so it uses the currently selected OpenRouter model. Use only `same-model-worker` and `same-model-reviewer`; both intentionally omit their model and inherit this primary model. Do not invoke model-pinned specialist agents. Plan, execute and review the task using the same model. Report the actual selected model alias. Task: $ARGUMENTS
