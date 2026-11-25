---
name: skill-authoring
description: Converts repeatable verified methods into clear and maintainable ReidX skill drafts
---

# Skill authoring

Create a proposed skill only when a method is repeatable and supported by evidence.

A skill must:
- Have a lowercase kebab-case name matching its folder name.
- Begin with YAML frontmatter containing `name` and `description`.
- State what it does and when it should be used.
- List prerequisites and required inputs.
- Give a numbered procedure with decision points.
- Include expected outputs and verification steps.
- Explain common failure modes and safe recovery.
- Avoid storing secrets, client-confidential details or brittle environment-specific values unless clearly parameterized.

Use `memory_memory_propose_skill` to place the draft in the skill review inbox. Do not edit active skill files directly. Include the task evidence and why the procedure generalizes.
