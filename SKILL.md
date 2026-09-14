---
name: on-the-record
description: Retrieval rules for answering questions from the on-the-record source-grounded expert knowledge base — cite only verified claims, with attribution.
---

# On the Record — retrieval rules

This skill governs how an agent answers questions using this repository's
`experts/`, `sources/`, and claim data. Follow these rules exactly; they
exist to keep every answer traceable back to something a human actually
confirmed.

## Core rule: cite verified, attribute always

- Only present a claim as something an expert said if its
  `verification.status` is `verified`.
- Every verified claim you use must be attributed: the expert's name,
  the show/source, and a link — build it from `verification.source_url`
  plus `verification.start_timestamp`–`verification.end_timestamp`.
- Never state a claim's content as true just because it's `verified`.
  `verification` only means the expert accurately said it — it says
  nothing about whether it's correct. If `evidence.excerpt` is present,
  you may surface it as separate supporting context, clearly labeled as
  such, not folded into the attribution.

## Handling non-verified claims

- `draft`, `unverified`, `reviewed`, and `rejected` claims exist in the
  data but must never be presented as something the expert established.
- If the only relevant material for a question is not `verified`, say so
  explicitly (e.g. "there's an unverified claim on this topic, but it
  hasn't been checked against the source yet") rather than presenting it
  as fact, or silently answering as if nothing exists.
- Never surface a `rejected` claim as if it were true or attributed —
  it was kept on record for auditability, not because it's usable.

## Cross-expert questions

A question naming multiple experts (or none, e.g. "who talks about X?")
should be answered by looking across all `experts/*.yaml` and all
`sources/*/*/claims.yaml`, not just one expert's files — pull every
`verified` claim relevant to the topic, grouped by expert, each with its
own citation. Don't imply agreement between experts that isn't actually
there in what was verified.

## Lookup path

1. Resolve which expert(s) and/or topic the question touches.
2. Find relevant sources under `sources/<show-slug>/<expert-slug>/`.
3. Scan `claims.yaml` for claims matching the topic with
   `verification.status: verified`.
4. Build the answer from those claims' `claim` text plus their
   attribution (expert, source, timestamp range, source_url).
5. If nothing verified matches, say so — don't fall back to `draft` or
   `unverified` claims as if they were usable.
