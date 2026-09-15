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

## Episodes, appearances, and people

Episode metadata (`title`, `url`, `platform`, `published_date`,
`duration`, `format`, `show`) is stored once per episode at
`sources/episodes/<episode-slug>.yaml` — never duplicated per person.
Every person who appeared in that episode (host, co-host, or guest)
gets their own thin appearance record at
`sources/<person-slug>/<episode-slug>/metadata.yaml`:

```yaml
id: <person-slug>-<episode-slug>
person: <person-slug>       # must match a people/<id>.yaml id
episode: <episode-slug>     # must match a sources/episodes/<id>.yaml id
role: host                  # host | co-host | guest
processing_status: pending  # pending | extracted | in_review | complete
```

`statements.yaml` lives alongside it, unchanged in shape from before.

## Adding a new episode by hand

1. Create `sources/episodes/<episode-slug>.yaml` with the episode's
   real metadata (see `schema/episode.schema.yaml`).
2. For the host, create
   `sources/<host-slug>/<episode-slug>/metadata.yaml` with `role: host`.
3. Run the extraction prompt against the real transcript to populate
   `draft` statements for the host's appearance.
4. Work statements through the verification statuses as you verify
   them against the real source.
5. Before committing, run:

   ```bash
   pip install -r requirements.txt
   python scripts/validate.py
   ```

## Adding a guest

Guests are registered in two separate, differently-costed phases —
never conflate them:

- **Phase A — register the person.** Run
  `python scripts/register_guests_phase_a.py` after adding new
  episodes. It sweeps episode titles and existing statements' `notes`
  fields for candidate guest names (no transcript re-fetching), tries
  to resolve each to an existing `people/*.yaml` by name/alias, and
  for unresolved names creates a stub person record —
  `identity_confidence: likely` or `uncertain`, `credentials`/`bio`
  left as placeholder `"TBD — ..."` text — plus a `role: guest`,
  `processing_status: pending` appearance record. **Never hand-write a
  `credentials`/`bio` value for a stub person** — only replace the
  placeholder once you've actually researched that person, the same
  way `people/nikhil-kamath.yaml` and `people/raj-shamani.yaml` were
  researched, and only then set `identity_confidence: confirmed`.
- **Phase B — extract the guest's statements.** For a specific guest's
  specific appearance (`role: guest`, `processing_status: pending`),
  re-read the real transcript and extract statements attributable
  *specifically to that guest* — the same conservative, per-episode
  process already used for hosts (see `prompts/extraction-prompt.md`),
  now additionally recording `speaker_confidence` (`high`/`medium`/
  `low`) on every statement, since no true audio diarization is
  available and attribution rests on textual signal only
  (self-identification, direct address, corroboration, turn-taking
  position). Document that reasoning in `notes`, exactly as already
  practiced throughout this corpus. This is not a batch job — treat it
  as an ongoing, per-guest, per-episode queue, the same way host
  extraction has been.

## Regenerating derived artifacts

Two generated files are never hand-edited, only regenerated:

- `STATS.md` — `python scripts/generate_stats.py`
- `profiles/<person-id>.md` — `python scripts/generate_profiles.py`,
  built only from `verified` statements; see SKILL.md's "Profiles are
  an index, not a source" section for how to use (not cite) them.
