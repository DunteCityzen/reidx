# Persistent Memory Index

The memory service indexes Markdown documents using the local Nomic Embed Text v1.5 model through LiteLLM. Semantic retrieval uses Nomic's `search_document:` and `search_query:` prefixes. Keyword search is available as a fallback.

## Categories
- `architecture.md`: host roles, network boundaries and harness architecture.
- `decisions.md`: durable design decisions and reasons.
- `lessons.md`: verified fixes, failures, caveats and command sequences.
- `workflows.md`: reusable task methodologies.
- `writing-style.md`: writing preferences and conventions.

## Operating rules
- Recall relevant entries before substantial tasks; do not dump the whole memory into every prompt.
- Date entries and include evidence/source context.
- Do not store API keys, passwords, personal data, client-confidential findings or unverified claims.
- Correct or supersede stale information rather than treating old notes as current.
- Create skill drafts in the skill inbox; active skills require user review and approval.
