---
name: single-model-lifecycle
description: Runs a task through planning, execution and review using the same primary OpenRouter model
---

# Single-model lifecycle

Use this skill when the user requests one model for every agent throughout a task.

1. Keep the current primary agent model for the entire lifecycle.
2. Delegate only to `same-model-worker` and `same-model-reviewer`; these agents intentionally have no model override and inherit the primary model.
3. Do not invoke pinned specialist agents in this mode.
4. Use one or two workers for independent read-only investigation when useful.
5. Have the primary agent or designated implementer perform edits.
6. Have `same-model-reviewer` independently assess the finished work.
7. Report the single model alias used and the agents involved.

To change the model for a single-model lifecycle, change the LiteLLM target behind the `orchestrator` alias or select a different configured primary model. Do not edit each generic worker.
