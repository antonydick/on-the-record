# Contributing

## Core principles

These three rules are invariant — every other convention in this repo
exists in service of them.

1. **Verification (attribution) and evidence (truth) are separate.**
   `verification` only answers "did the person accurately say this, and
   where." `evidence` only answers "is this actually true." A statement
   can be fully verified and still false, contested, or unassessed —
   never let a `verified` status imply the content is correct.
2. **`verified` has a strict evidentiary bar.** A statement only
   reaches `verified` once a human has re-checked the primary source
   and recorded `source_url`, `start_timestamp`, `end_timestamp`, and
   `verified_at`. All four are required together — the validator
   enforces this.
3. **Rejected statements are preserved, never deleted.** If a statement
   turns out to be inaccurate or misattributed, set
   `verification.status: rejected` and explain why in `notes`. Keeping
   it on record — rather than silently removing it — is what makes the
   verification process auditable.

## Never invent statement content

Never write, complete, or "fill in" statement text yourself, or set a
statement's status to anything other than `draft` without having
actually checked it. A statement only ever earns a non-`draft` status
because a human did the corresponding work against the real source.
This applies especially to statements attributed to real people — do
not invent what a real person said, in any status.

## A statement belongs to one source; never pre-write the connections

Each statement is grounded in exactly one appearance. If a person says
related things across several appearances, extract and verify each
occurrence as its own independent statement — do not write a statement
that summarizes or connects things said across multiple sources.
Constructing that narrative (e.g. "over three interviews, they
described a progression from X to Y to Z") is an agent's job at answer
time, done by pulling several independently-attributed `verified`
statements — see [SKILL.md](SKILL.md). Pre-writing that connection into
the data would hide which parts were actually said versus inferred.

## Verification workflow

Each statement moves through `verification.status` as follows:

1. **`draft`** — pulled from a transcript via
   [`prompts/extraction-prompt.md`](prompts/extraction-prompt.md). Not
   yet touched by a human.
2. **`unverified`** — a human has entered or edited the statement (e.g.
   fixed obvious extraction errors) but hasn't checked it against the
   primary source yet.
3. **`reviewed`** — a human has read the statement and believes it's
   plausible, but hasn't re-checked the primary recording/text at a
   specific timestamp. A soft signal, not a citation-ready state.
4. **`verified`** — a human went back to the primary source, confirmed
   the person said this, and recorded exactly where:
   - `source_url`: a deep link to the clip/passage
   - `start_timestamp` / `end_timestamp`: the span in the source
   - `verified_at`: the date this check was done
   - `verified_by`: who did it (recommended)
5. **`rejected`** — checked and found inaccurate, misattributed, or
   unsupportable. Explain why in `notes`. Never delete a rejected
   statement.

## Source processing status

Independent of any single statement, each `sources/*/*/metadata.yaml`
file tracks `processing_status` for that appearance as a whole:

- `pending` — registered, nothing extracted yet
- `extracted` — draft statements pulled from the transcript
- `in_review` — at least one statement has been looked at by a human
- `complete` — every statement from this appearance has reached
  `verified` or `rejected`

## Adding a new person / appearance

1. Copy `people/example-person.yaml` to `people/<id>.yaml`, filling in
   real, public identity info only (name, credentials, bio).
2. For each appearance, create
   `sources/<person-slug>/<interviewer-slug>/metadata.yaml` and
   `statements.yaml`, following `sources/example-person/` as a
   structural template — not as a source of real content. A person with
   several appearances gets several `<interviewer-slug>` directories
   under the same `sources/<person-slug>/`, regardless of who
   interviewed them each time.
3. Run the extraction prompt against the real transcript to populate
   `draft` statements for that one appearance.
4. Work statements through the statuses above as you verify them
   against the real source.
5. Before committing, run:

   ```bash
   pip install -r requirements.txt
   python scripts/validate.py
   ```
