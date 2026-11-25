---
name: multi-model-review
description: Runs a controlled parallel review using independent specialist models
---

# Multi-model review

1. Define a review question and acceptance criteria.
2. Select no more than three reviewers whose roles differ meaningfully.
3. Start independent read-only agents concurrently. Typical choices: `security-analyst`, `code-reviewer`, `evaluator`, `researcher` or `vision-analyst`.
4. Give each reviewer the same source material and criteria, but do not show one reviewer's conclusions to another before their independent review completes.
5. Require evidence, confidence, severity where relevant, and explicit limitations.
6. Compare findings. Deduplicate matching findings and preserve genuine disagreements.
7. Ask for targeted verification when a disagreement affects the outcome.
8. The coordinator produces the consolidated result. Reviewers do not edit source files.
9. Record the aliases actually used and any model failures or substitutions.

Do not treat provider fallback as independent evaluation. Do not exceed three concurrent free-model workers by default.
