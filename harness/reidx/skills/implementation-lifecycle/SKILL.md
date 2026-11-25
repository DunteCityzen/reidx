---
name: implementation-lifecycle
description: Coordinates safe software and configuration changes from requirements through implementation, testing and independent review
---

# Implementation lifecycle

Use this workflow when the user has explicitly asked for a code, script, infrastructure-as-code or configuration change.

## Phase 1 — Understand and recall
1. Read the project instructions and inspect the relevant repository structure.
2. Search persistent memory for previous decisions, lessons and similar implementations.
3. Identify the requested outcome, scope, constraints, affected files, dependencies and rollback considerations.
4. Do not infer missing production values, credentials, network ranges or destructive scope.

## Phase 2 — Plan
1. Ask `architect` for a short implementation plan when the change spans multiple files or has meaningful dependencies.
2. Define acceptance criteria before editing.
3. Separate work that can happen independently from work that must be sequential.
4. Identify configuration compatibility and security implications.

## Phase 3 — Pre-change investigation
1. Use up to three read-only specialists when they add value: `researcher`, `security-analyst` and/or `code-reviewer`.
2. Give each specialist a clearly bounded work package and the same source-of-truth context where relevant.
3. Require evidence and distinguish confirmed facts from hypotheses.
4. Do not allow investigation agents to modify the target files.

## Phase 4 — Implementation
1. Assign all changes to one `implementer` for the shared file set.
2. Inspect current contents before editing. Preserve existing user configuration unless replacement was explicitly requested.
3. Make small, reversible changes. Back up high-impact configuration before replacement.
4. Keep secrets out of source files, command output and persistent memory.
5. Do not run destructive commands or change production services without explicit approval.

## Phase 5 — Verification
1. Ask `test-engineer` to identify and run narrowly scoped, non-destructive tests with approval where required.
2. Run `code-reviewer` independently against the diff or changed files. These two reviews may run concurrently if they do not modify files.
3. Correct material defects through the same designated implementer; do not introduce competing writers.
4. Ask `evaluator` for a final review when the change is substantial, security-sensitive or user-facing.
5. Record exact commands and observed results. A syntactically valid configuration is not proof that its service works.

## Phase 6 — Completion and learning
1. Summarize changed files, tests, observed results, unresolved issues and rollback information.
2. Capture only durable, verified lessons using `memory_memory_remember`.
3. Propose a skill only when a method is repeatable, generalizable and supported by evidence.
4. Keep skill drafts inactive until the user reviews and promotes them.

## Parallelism and ownership
- Default maximum: three concurrent read-only specialists.
- One implementer owns modifications to a shared file set.
- Testing and review may run concurrently after implementation.
- Do not start all available agents automatically; delegate only when their distinct perspectives justify their cost and free-tier requests.
