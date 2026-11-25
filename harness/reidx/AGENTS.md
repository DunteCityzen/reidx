# Global ReidX Harness Instructions

These instructions apply to ReidX sessions using this global configuration.

## Architecture and model boundaries
- ReidX is the agent orchestrator. LiteLLM is the model gateway. OpenRouter supplies the configured cloud inference models. Ollama on Impala supplies local models and the Nomic embedding model.
- All primary and specialist agent profiles must use `litellm/<role-alias>` aliases mapped to OpenRouter models in LiteLLM.
- Do not assign local chat models to ReidX primary agents or subagents. Local aliases remain available only for deliberate manual testing.
- The `nomic-embed` alias is reserved for local embeddings and memory retrieval; it is not a chat agent.
- Never change provider model IDs inside agent files. Change the role mapping in LiteLLM `config.yaml` instead.

## Task selection
- Before substantial work, recall relevant memory using the `memory` MCP tools and read the relevant skills.
- Choose one of two execution strategies:
  1. Single-model lifecycle: enter the `single-model` primary agent. It intentionally has no model override and uses the currently selected OpenRouter model. Use only `same-model-worker` and `same-model-reviewer`, which inherit that primary model.
  2. Specialist lifecycle: delegate to the named specialist agents whose role aliases are pinned in their agent files.
  3. Five-model panel: only when explicitly requested, use all five `panel-*` agents in two waves (three, then two). The waves are an orchestration policy; LiteLLM does not provide a proxy-wide concurrency semaphore in this configuration.
- For trivial tasks, do not spawn subagents.
- For substantial tasks, create a short plan, define acceptance criteria, and use the minimum number of agents that adds real value.
- Default maximum parallel specialist calls: three. This is an ReidX workflow policy, not a hard global semaphore. LiteLLM limits requests per deployment; free OpenRouter endpoints also have account/provider request/day and request/minute limits. Do not fan out merely because agents are available.
- Parallelize independent research, analysis and review. In specialist workflows, Build and Writer coordinate without editing; use one designated `implementer` or `writer-specialist` to modify a given set of files. In single-model mode, the selected primary may own the edits.
- Do not allow multiple agents to edit the same files concurrently.

## Evidence and verification
- Inspect before changing. Do not claim a command, test, deployment or file change succeeded without tool output confirming it.
- Separate verified facts, assumptions, hypotheses and recommendations.
- In security work, distinguish confirmed vulnerabilities from potential weaknesses; provide reproducible evidence and impact reasoning.
- Preserve relevant command output, source references and test results in task artifacts where appropriate.
- Ask before destructive actions, production changes, external network scans, credential handling, or actions outside the user's stated scope.

## Persistent memory and learning
- Use `memory_memory_search` before substantial tasks to recall previous decisions, lessons, methodologies and writing preferences.
- After a substantial task, capture durable verified lessons with `memory_memory_remember`.
- Do not store secrets, API keys, personal data, client-confidential information or unverified claims in persistent memory.
- Use `memory_memory_propose_skill` to create draft skills in the skill inbox. Never overwrite or activate an existing skill without explicit user approval.
- A learning note is not automatically a reusable skill. Promote a method only when it is repeatable, evidence-backed and generalizable.
- Keep memory concise, dated, categorized and easy to supersede when facts change.

## Writing
- Preserve the user's natural voice. Avoid generic AI phrasing, inflated claims, marketing language and unnecessary headings.
- Technical reports must distinguish scope, methodology, evidence, impact, limitations and remediation.
- Blog and LinkedIn drafts should sound human and specific, not like generic corporate announcements.
- Do not invent project facts, test results, client details, metrics or quotations.

## Completion format
For substantial work, report:
- What was done
- Files/artifacts changed
- Tests and verification performed
- Findings not independently verified
- Outstanding work and risks
- Reusable lessons captured or skill drafts proposed
