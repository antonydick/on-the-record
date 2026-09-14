---
name: on-the-record
description: Retrieval rules for answering questions from the on-the-record source-grounded memory layer for people who've spoken publicly — cite only verified statements, with attribution, and never blur direct quotes with inferred narrative.
---

# On the Record — retrieval rules

This skill governs how an agent answers questions using this
repository's `people/`, `sources/`, and statement data. Follow these
rules exactly; they exist to keep every answer traceable back to
something a human actually confirmed a person said.

## Core rule: cite verified, attribute always

- Only present a statement as something a person said if its
  `verification.status` is `verified`.
- Every verified statement you use must be attributed: the person's
  name, the source appearance, and a link — build it from
  `verification.source_url` plus `verification.start_timestamp`–
  `verification.end_timestamp`.
- Never state a statement's content as true just because it's
  `verified`. `verification` only means the person accurately said it —
  it says nothing about whether it's correct. If `evidence.excerpt` is
  present, you may surface it as separate supporting context, clearly
  labeled as such, not folded into the attribution.

## Handling non-verified statements

- `draft`, `unverified`, `reviewed`, and `rejected` statements exist in
  the data but must never be presented as something the person
  established.
- If the only relevant material for a question is not `verified`, say
  so explicitly (e.g. "there's an unverified statement on this topic,
  but it hasn't been checked against the source yet") rather than
  presenting it as fact, or silently answering as if nothing exists.
- Never surface a `rejected` statement as if it were true or attributed
  — it was kept on record for auditability, not because it's usable.

## Never blur what was said with what you're inferring

This is the rule that matters most for multi-statement answers. A
statement is always grounded in exactly one source. Any narrative,
progression, or pattern you construct by connecting statements from
different appearances (e.g. "they described struggling with X, then
learning from Y, then later doing Z differently") is *your*
construction, not something stored or attributed as a single fact.

- When you synthesize across statements, structure the answer so each
  underlying statement keeps its own attribution (person, source,
  timestamp) — e.g. as a timeline or list — rather than folding them
  into one unattributed paragraph.
- Explicitly separate what the person directly said (each individual
  verified statement) from any connective interpretation you're adding
  (e.g. "across these N appearances, a progression emerges — this
  interpretation is not itself a statement any single source makes").
- If someone could reasonably read your answer and think the person
  said the *connecting* narrative in one place, rephrase — that
  misattributes your synthesis to them.

## Three retrieval capabilities

1. **Longitudinal reconstruction** — "What has this person said, across
   everything they've recorded, about topic X?" Search every
   `sources/<person>/*/statements.yaml` for that person, not just one
   appearance. This is the primary use case: important things a person
   has said are often scattered across many appearances, each
   mentioning it only briefly.
2. **Cross-person comparison** — "What do these people agree or
   disagree on?" Pull `verified` statements on the same topic across
   multiple `people/`, grouped by person, and note agreement/disagreement
   only where the statements themselves support it — don't infer shared
   ground that isn't actually there in what was verified.
3. **Cross-source synthesis** — patterns that emerge only by looking
   across many people's statements together (e.g. a theme several
   people independently raise). Treat this the same as longitudinal
   reconstruction's inference rule above: keep each contributing
   statement attributed, and label the pattern itself as your synthesis.

## Lookup path

1. Resolve which person/people and/or topic the question touches.
2. Find relevant sources under `sources/<person-slug>/*/` — for a
   longitudinal question, that means *all* subdirectories for that
   person, not just one.
3. Scan each `statements.yaml` for statements matching the topic with
   `verification.status: verified`.
4. Build the answer from those statements' `text` plus their
   attribution (person, source, timestamp range, source_url), keeping
   each one separately attributed per the rule above.
5. If nothing verified matches, say so — don't fall back to `draft` or
   `unverified` statements as if they were usable.
