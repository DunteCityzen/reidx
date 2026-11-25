---
name: task-orchestration
description: Selects the right workflow, decomposes substantial tasks and coordinates agents efficiently
---

# Task orchestration

1. Read global `AGENTS.md` and recall relevant memory using `memory_memory_search`.
2. Classify the task: simple response, research, implementation, security assessment, writing, or mixed.
3. For simple tasks, do not delegate.
4. For substantial tasks, define objective, scope, constraints, deliverables and acceptance tests.
5. Choose one lifecycle:
   - Single-model: use `same-model-worker` and `same-model-reviewer` only. They inherit the primary model.
   - Specialist: use pinned specialist agents by role.
6. Run at most three independent subagents concurrently by default. Do not fan out all agents automatically.
7. Keep one designated implementer for each shared file set. Reviewers and researchers are read-only.
8. Consolidate findings, resolve disagreements with evidence and request verification where needed.
9. Capture durable learning after substantial tasks.

Do not claim that aliases automatically select a task-specific model. The primary agent and explicit subagent definitions determine model assignments.
