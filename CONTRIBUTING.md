# Contributing

## Core principles

These three rules are invariant — every other convention in this repo
exists in service of them.

1. **Verification (attribution) and evidence (truth) are separate.**
   `verification` only answers "did the expert accurately say this, and
   where." `evidence` only answers "is this actually true." A claim can
   be fully verified and still false, contested, or unassessed — never
   let a `verified` status imply the content is correct.
2. **`verified` has a strict evidentiary bar.** A claim only reaches
   `verified` once a human has re-checked the primary source and
   recorded `source_url`, `start_timestamp`, `end_timestamp`, and
   `verified_at`. All four are required together — the validator
   enforces this.
3. **Rejected claims are preserved, never deleted.** If a claim turns
   out to be inaccurate or misattributed, set `verification.status:
   rejected` and explain why in `notes`. Keeping it on record — rather
   than silently removing it — is what makes the verification process
   auditable.

## Never invent claim content

Never write, complete, or "fill in" claim text yourself, or set a
claim's status to anything other than `draft` without having actually
checked it. A claim only ever earns a non-`draft` status because a human
did the corresponding work against the real source. This applies
especially to claims attributed to real people — do not invent what a
real expert said, in any status.

## Verification workflow

Each claim moves through `verification.status` as follows:

1. **`draft`** — pulled from a transcript via
   [`prompts/extraction-prompt.md`](prompts/extraction-prompt.md). Not
   yet touched by a human.
2. **`unverified`** — a human has entered or edited the claim (e.g.
   fixed obvious extraction errors) but hasn't checked it against the
   primary source yet.
3. **`reviewed`** — a human has read the claim and believes it's
   plausible, but hasn't re-checked the primary recording/text at a
   specific timestamp. A soft signal, not a citation-ready state.
4. **`verified`** — a human went back to the primary source, confirmed
   the expert said this, and recorded exactly where:
   - `source_url`: a deep link to the clip/passage
   - `start_timestamp` / `end_timestamp`: the span in the source
   - `verified_at`: the date this check was done
   - `verified_by`: who did it (recommended)
5. **`rejected`** — checked and found inaccurate, misattributed, or
   unsupportable. Explain why in `notes`. Never delete a rejected claim.

## Source processing status

Independent of any single claim, each `sources/*/*/metadata.yaml` file
tracks `processing_status` for the source as a whole:

- `pending` — registered, nothing extracted yet
- `extracted` — draft claims pulled from the transcript
- `in_review` — at least one claim has been looked at by a human
- `complete` — every claim from this source has reached `verified` or
  `rejected`

## Adding a new expert / source

1. Copy `experts/example-expert.yaml` to `experts/<id>.yaml`, filling in
   real, public identity info only (name, credentials, bio).
2. Create `sources/<show-slug>/<expert-slug>/metadata.yaml` and
   `claims.yaml`, following `sources/example-show/example-expert/` as a
   structural template — not as a source of real content.
3. Run the extraction prompt against the real transcript to populate
   `draft` claims.
4. Work claims through the statuses above as you verify them against
   the real source.
5. Before committing, run:

   ```bash
   pip install -r requirements.txt
   python scripts/validate.py
   ```
