---
name: five-model-panel
description: Runs an independent review across all five currently configured OpenRouter model families in controlled waves
---

# Five-model panel

Use this workflow only when the user explicitly asks for a broad multi-model comparison or independent panel. Do not run it for every ordinary task.

## Panel members
- `panel-nemotron`: high-capacity reasoning and orchestration perspective.
- `panel-inkling`: general reasoning and alternative interpretation.
- `panel-xing`: engineering, planning and tool-use perspective.
- `panel-dots`: code, evidence and long-context review.
- `panel-super-vl`: multimodal-capable review; use supplied images/documents when relevant, and text-only review otherwise.

## Execution
1. Define a single task statement, shared source material and explicit evaluation criteria.
2. Ask all five panel agents to work independently. Do not share one panel member's answer with another before their first response.
3. Run in two waves: first three agents, wait for completion, then the remaining two. This is a workflow-level concurrency policy; it is not enforced by a proxy-wide LiteLLM semaphore.
4. Each panel member must return: conclusion, evidence, assumptions, confidence, limitations, and recommendations. For code/security findings, include file/line or reproducible evidence.
5. Do not let panel members edit files or execute commands. This is an evaluation workflow, not implementation.
6. Compare agreement and disagreement. Do not majority-vote away a well-supported minority finding.
7. Where disagreement changes the outcome, request a targeted verification from the appropriate specialist or test engineer.
8. Consolidate the result and record the exact panel aliases/models used, failures, and unavailable endpoints.
9. Do not automatically persist raw panel responses. Save only durable, verified lessons after review.

## Quota and privacy
- All five models use free OpenRouter variants and consume the account's request allowance. Use this workflow selectively.
- If a provider returns 429/503 or is unavailable, record it. Do not silently substitute a different model.
- Do not send client-confidential, personal, credential or otherwise sensitive information to free cloud endpoints.
