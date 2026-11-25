# Workflow Memory

## Single-model lifecycle
Use the primary Build/Plan/Research/Writer model for all work. Delegate only to `same-model-worker` and `same-model-reviewer`, which intentionally have no model override and inherit the parent model. Do not invoke pinned specialist agents in this mode.

## Specialist lifecycle
Use pinned specialist agents based on task type. Default maximum three concurrent agents. Parallelize independent research/review, not concurrent edits to shared files. Use one designated implementer.

## Continuous learning
At task completion: search memory, capture verified durable lesson(s), identify repeated methods, draft a skill candidate only when generalizable, and leave it for user review.
