# Extraction prompt

Use this prompt (with an LLM, against a transcript) to pull *candidate*
statements out of a new appearance into `draft` status, ready for a
human to verify. It never determines accuracy or verification status
itself, and it never connects statements across different appearances —
that judgment belongs entirely to a human contributor (verification) or
to an agent at answer time (synthesis across sources), per
[CONTRIBUTING.md](../CONTRIBUTING.md) and [SKILL.md](../SKILL.md).

---

You are extracting candidate statements from one interview/appearance
transcript for a source-grounded knowledge base about a specific
person. You are not verifying anything, and you are not connecting this
to anything the person said elsewhere — you are only identifying things
they said *in this transcript* that are worth capturing for a human to
later check against the recording.

For each transcript, produce entries matching this shape:

```yaml
- id: <person-slug>-<NNN>          # sequential, unique within this person
  person: <person-slug>
  source: <source-id>
  type: assertion | experience | belief | recommendation | observation | mechanism | evidence | qualification | example
  text: >
    The statement, in the person's own words as closely as possible.
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
- Leave `evidence.excerpt` as `null`. Assessing whether a statement's
  content is true is a separate, later step — not part of extraction.
- Pick the single best-fitting `type` for each statement:
  - `assertion` — a general statement that doesn't fit any type below.
  - `experience` — a first-person memory, story, or lived event
    ("I struggled with X," "when I was 18, I did Y").
  - `belief` — a subjective opinion, value judgment, or prediction.
  - `recommendation` — prescriptive advice ("you should do X").
  - `observation` — something noticed or reported as fact.
  - `mechanism` — explains how or why something works.
  - `evidence` — the person citing or referencing someone else's work
    or a study.
  - `qualification` — a caveat, condition, or exception attached to
    something else they said.
  - `example` — a concrete illustrative instance.
- Prefer more, smaller statements over fewer, bundled ones — each
  statement should be independently checkable against one place in the
  recording. Small, easy-to-miss statements — a passing remark, one
  sentence in a much longer answer about something else — are exactly
  what this project exists to capture; don't skip them because they
  seem minor or tangential to the episode's main topic.
- Do not paraphrase away specifics (numbers, mechanisms, conditions,
  names) — a verifier needs enough detail to confirm or reject the
  statement later.
- Do not summarize, connect, or draw conclusions across multiple things
  the person says in this transcript (e.g. don't write "the person
  describes a progression from X to Y") — extract each as its own
  independent statement. Connecting statements into a narrative happens
  only when an agent answers a question by pulling `verified` statements
  from across multiple sources — never at extraction time, and never
  written into stored data.
- If you're unsure whether something is a statement worth capturing at
  all, leave it out rather than guessing.
