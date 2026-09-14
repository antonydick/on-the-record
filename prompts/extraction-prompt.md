# Extraction prompt

Use this prompt (with an LLM, against a transcript) to pull *candidate*
claims out of a new interview into `draft` status, ready for a human to
verify. It never determines accuracy or verification status itself —
that judgment belongs entirely to a human contributor, per
[CONTRIBUTING.md](../CONTRIBUTING.md).

---

You are extracting candidate claims from an interview transcript for a
source-grounded knowledge base. You are not verifying anything — you are
only identifying things the expert said that are worth capturing for a
human to later check against the recording.

For each transcript, produce entries matching this shape:

```yaml
- id: <expert-slug>-<NNN>          # sequential, unique within this expert
  expert: <expert-slug>
  source: <source-id>
  type: finding | recommendation | anecdote | opinion | definition | citation
  claim: >
    The claim, in the expert's own words as closely as possible.
  topic: <short topic slug>
  verification:
    status: draft
    verified_at: null
    verified_by: null
    source_url: null
    start_timestamp: null
    end_timestamp: null
  evidence:
    excerpt: null
  notes: "Approximate transcript location, if known, to help the human verifier."
```

Rules:

- `verification.status` is always `draft`. Never write `unverified`,
  `reviewed`, `verified`, or `rejected` — you have not checked anything
  against the primary source, only against the transcript text.
- Leave every field under `verification` other than `status` as `null`.
  Filling in a timestamp or URL you haven't confirmed against the actual
  recording would misrepresent it as checked.
- Leave `evidence.excerpt` as `null`. Assessing whether a claim's content
  is true is a separate, later step — not part of extraction.
- Pick the single best-fitting `type` for each claim. If a statement
  reports a study or study-like result, that's `finding`; a "you should
  do X" is `recommendation`; a first-person story is `anecdote`; a
  subjective view or forecast is `opinion`; explaining what a term means
  is `definition`; explicitly citing someone else's work is `citation`.
- Prefer more, smaller claims over fewer, bundled ones — each claim
  should be independently checkable against one place in the recording.
- Do not paraphrase away specifics (numbers, mechanisms, conditions) —
  a verifier needs enough detail to confirm or reject the claim later.
- If you're unsure whether something is a claim worth capturing at all,
  leave it out rather than guessing.
