# Guest profiles & multi-episode person reconstruction

Status: approved for planning
Date: 2026-09-15

## Problem

Today, `on-the-record` only tracks the two show hosts (Nikhil Kamath,
Raj Shamani) as `people/`. Every guest who appears alongside them —
co-founders, panelists, one-off interviewees — exists only as free
text inside a statement's `notes:` field, used solely to justify why a
line was attributed to the host and not a guest. Guests are never
themselves a tracked entity, never get their own appearance record,
and never get their own statement corpus.

This spec extends the existing source-grounded model so that **every**
person who appears in the corpus — host or guest — is a first-class,
persistent entity, reconstructable across every appearance they've
ever made, while preserving every existing invariant: verification is
never evidence, a statement is never fabricated, and synthesis is
never presented as something a person said.

## Non-goals

- Not a general-purpose AI biography generator. Profiles only ever
  organize pointers to `verified` statements — never freeform prose
  asserted as fact.
- Not real audio diarization. No diarization tool/service is wired
  into this environment; this spec formalizes LLM-inferred, textually
  justified speaker attribution instead (see "Speaker confidence").
- Not a promise that all guest statement extraction happens in one
  pass. See "Rollout phases" — registering guest *people* and
  extracting guest *statements* are different orders of magnitude of
  work and are explicitly sequenced apart.

## Data model changes

### New: `schema/episode.schema.yaml`

An episode's facts, stored once regardless of how many people appeared
in it.

```yaml
$id: episode.schema.yaml
type: object
required: [id, title, url, platform, published_date, format]
properties:
  id:
    type: string
    pattern: "^[a-z0-9]+(-[a-z0-9]+)*$"
    description: Slug matching the filename (sources/episodes/<id>.yaml).
  title: { type: string }
  url: { type: string, format: uri }
  platform: { type: string, enum: [youtube, podcast, article, book, other] }
  published_date: { type: string, format: date }
  duration: { type: string }
  format: { type: string, enum: [podcast, video, article, book] }
  show:
    type: string
    description: >
      Free-text series/show name, e.g. "WTF is" or "Figuring Out with
      Raj Shamani". Not a foreign key — purely descriptive.
additionalProperties: false
```

File location: `sources/episodes/<episode-slug>.yaml`. `<episode-slug>`
must be globally unique across the whole repo (existing slugs already
namespace by show — `wtf-is-chatgpt-ep4`, `fo561-smriti-mandhana` — so
collisions are not expected in practice, but the validator enforces
uniqueness explicitly rather than assuming it).

### Redefined: `schema/source.schema.yaml`

A "source" stops being "one person's copy of an episode's metadata"
and becomes **one person's appearance in an episode**.

```yaml
$id: source.schema.yaml
type: object
required: [id, person, episode, role, processing_status]
properties:
  id: { type: string }
  person:
    type: string
    description: Must match a people/<id>.yaml id.
  episode:
    type: string
    description: Must match a sources/episodes/<id>.yaml id.
  role:
    type: string
    enum: [host, co-host, guest]
  processing_status:
    type: string
    enum: [pending, extracted, in_review, complete]
additionalProperties: false
```

Directory: `sources/<person-slug>/<episode-slug>/metadata.yaml` +
`statements.yaml`, unchanged in location and unchanged in
`statements.yaml`'s own shape. The directory's second segment must
equal the appearance's `episode` field (replacing the old
`interviewer_slug` match-check). `interviewer_slug` is removed —
episodes are shared, so "who interviewed them" is no longer this
file's job; it's implicit in `role` plus the episode's own metadata.

`statement.source` continues to resolve exactly as before — it points
at an appearance id, and appearance ids are unaffected by this
migration.

### Extended: `schema/person.schema.yaml`

Adds three optional fields, additive and backward-compatible with the
three existing person records:

```yaml
aliases:
  type: array
  items: { type: string }
  description: >
    Other names/spellings this person is known by in source material
    (e.g. "Nikhil", "Nikhil Kamath (WTF)"), used to resolve mentions to
    this canonical record without creating a duplicate.
organization:
  type: string
  description: Optional current primary organization/affiliation.
identity_confidence:
  type: string
  enum: [confirmed, likely, uncertain]
  default: confirmed
  description: >
    confirmed = a human created or reviewed this record. likely = the
    record was auto-created from a strong signal (e.g. explicit name
    in an episode title or in another statement's notes) but not yet
    human-reviewed. uncertain = weak/ambiguous signal; the record
    exists so statements aren't orphaned, but identity should be
    treated as provisional until confirmed.
```

`identity_confidence` defaults to `confirmed` so the three existing
person records need no changes to stay valid.

### Extended: `schema/statement.schema.yaml`

Adds one optional field:

```yaml
speaker_confidence:
  type: string
  enum: [high, medium, low]
  description: >
    How confident the extraction was that this line belongs to
    `person` specifically, given no true audio diarization is
    available — only textual signal (self-identification, direct
    address by name, host-framing, corroboration). high = explicit
    self-identification or unambiguous framing. medium = strong
    contextual inference (e.g. turn-taking position, recurring
    show-segment pattern). low = plausible but weakly supported;
    should be treated cautiously at verification time. Optional for
    backward compatibility with pre-existing statements, but required
    in practice (enforced by CONTRIBUTING.md, not the schema) for any
    new statement attributed to a guest.
```

Kept optional at the schema level (not `required`) so the 239 existing
statements remain valid without a mass rewrite; the migration script
(below) backfills a value onto all of them anyway so the field is
populated in practice from day one.

## Migration plan

One-time script, `scripts/migrate_to_episodes.py`, run once and then
deleted (not a permanent part of the pipeline):

1. For each existing `sources/<person>/<slug>/metadata.yaml`: write
   `sources/episodes/<slug>.yaml` with the episode-level fields
   (`title`, `url`, `platform`, `published_date`, `duration`,
   `format`), plus `show` inferred from the person (`"WTF is"` for
   nikhil-kamath sources, `"Figuring Out with Raj Shamani"` for
   raj-shamani sources).
2. Rewrite that `metadata.yaml` down to the new appearance shape:
   `id` (unchanged), `person` (unchanged), `episode: <slug>`,
   `role: host`, `processing_status` (unchanged).
3. Leave every `statements.yaml` file untouched in content; add
   `speaker_confidence: high` to each existing statement (all 239 are
   host self-attributions, already individually justified in `notes`
   at length — `high` is the correct retroactive value, not a
   placeholder guess).
4. Run `scripts/validate.py` after migration; the run is only
   considered done when it reports the same total statement count
   (239) and the new episode/appearance counts line up (125 episodes,
   125 appearances, all `role: host`).
5. Update `scripts/validate.py` itself for the new cross-file checks:
   `source.episode` must resolve to a real `sources/episodes/*.yaml`
   id; the directory's second path segment must equal `episode`
   (replacing the old `interviewer_slug` check); episode ids must be
   unique.
6. Commit the migration as its own single commit, separate from any
   guest-registration work, so it can be reviewed/reverted
   independently.

`sources/example-person/` and its two example appearances are migrated
too, for consistency, and to keep serving as an accurate structural
template — its placeholder content stays clearly marked as before.

## Guest discovery workflow

Split deliberately into two phases of very different cost, per the
brainstorming discussion — conflating them was the main scope risk in
the original request.

### Phase A — register guest *people* (cheap, mechanical, safe to do in one pass)

For each of the 125 episodes, without re-fetching any transcript:

1. Parse the episode title for named guests (most already follow a
   consistent "Ft. X, Y & Z" or "| Guest Name |" pattern).
2. Scan that episode's existing `statements.yaml` `notes:` fields,
   which frequently already name co-guests in prose (established
   practice from the host-attribution discipline used throughout this
   corpus so far).
3. For each distinct guest name surfaced, attempt to resolve against
   an existing `people/*.yaml` `name`/`aliases` (fuzzy match on
   normalized name). If resolved, link this appearance to the existing
   person. If not resolved, create a new `people/<slug>.yaml` stub:
   `name` (as it appeared), `credentials: "TBD — identity not yet
   confirmed"`, `bio: "TBD — auto-registered from episode title/notes,
   not yet researched."`, `identity_confidence: likely` (or
   `uncertain` if the name signal was ambiguous — e.g. only a first
   name, or a title like "Dr. K").
4. Create the guest's appearance record (`role: guest`,
   `processing_status: pending` — no statements yet) under
   `sources/<guest-slug>/<episode-slug>/metadata.yaml`.
5. Never invent a bio. A stub person record with `identity_confidence`
   below `confirmed` and placeholder `credentials`/`bio` text is
   explicitly allowed and expected at this phase — it is not the same
   as fabricating claims about someone, and is clearly marked as
   unconfirmed. A human (or a later, explicit research pass, the same
   way `people/nikhil-kamath.yaml` and `people/raj-shamani.yaml` were
   researched) upgrades `identity_confidence` to `confirmed` and
   replaces the placeholder bio with real, sourced information before
   it's treated as reliable.

This phase is what unblocks cross-episode questions like "who has
appeared with Nikhil more than once" even before any guest statement
has been extracted.

### Phase B — extract guest *statements* (expensive, ongoing, episode-by-episode)

Unchanged in kind from the existing host-extraction pipeline: for a
given guest's given appearance, re-read the real transcript, extract
`draft` statements attributable to that specific guest (not the host,
not other guests), following the same conservative attribution
discipline already established (self-identification, direct address,
corroboration — now recorded via the new `speaker_confidence` field
instead of prose-only). This is a queue, not a batch job — the same
order of magnitude of work as the "Finish Nikhil's" effort, multiplied
by however many guests are prioritized. This spec does not schedule
Phase B to completion; it establishes the pipeline and the schema so
it can proceed guest-by-guest, exactly as host extraction did
episode-by-episode.

## Profile generation

`scripts/generate_profiles.py`, modeled on the existing
`generate_stats.py`:

- Input: every `people/*.yaml` record, every appearance under
  `sources/<person>/*/`, every statement in each appearance's
  `statements.yaml`.
- Filter: **only** statements with `verification.status: verified`.
  This is a direct, deliberate consequence of the existing
  verification bar, not a new rule — but it means profiles will be
  **near-empty immediately after this ships**, since effectively
  nothing in the corpus is `verified` yet (239 Nikhil statements are
  `draft`; Raj and all new guests currently have none). This is
  correct behavior — a profile must never synthesize from unverified
  content — and is called out here so it isn't mistaken for a bug when
  the first generated profiles come back mostly empty.
- Output: `profiles/<person-id>.md`, one file per person, regenerated
  in full each run (never hand-edited — a stale profile after a
  statement is edited/rejected/reassigned is exactly the failure mode
  this rule prevents). Structure, per the categories in the original
  request:
  - Background, Beliefs & principles, Experiences & stories, Opinions,
    Recurring ideas (grouped by topic where ≥2 verified statements
    across ≥2 different appearances share a `topic`), Evolution
    (flagged only where ≥2 verified statements on the same topic exist
    with different `published_date`s — worded per SKILL.md's existing
    caution: "later stated," "differs from an earlier statement,"
    never "changed his mind" unless a statement itself says so),
    Relationships & references (people/companies/books mentioned
    across ≥2 verified statements).
  - Every line is a reference — `[statement text excerpt] — see
    <statement-id> (<episode title>, <date>)` — never freestanding
    prose. No line in this file is ever a citable fact on its own; it
    is an index back to the statement.
- Regeneration trigger: run manually (`python scripts/generate_profiles.py`),
  same as `generate_stats.py` today — no new automation/CI step in
  this spec's scope.

## SKILL.md update

One new short section, "Profiles are an index, not a source": a
profile file may be used to *discover* which statements are relevant
to a question, but an answer must still resolve to and cite the
underlying `verified` statement(s) directly — a profile line is never
itself quoted or cited as the source.

## CONTRIBUTING.md update

- Document the new `sources/episodes/` layer and the appearance model
  replacing the old per-person metadata duplication.
- Document `role`, `speaker_confidence`, and the Phase A/Phase B split
  for guest onboarding.
- Document `identity_confidence` and when a stub person record is
  acceptable vs. when it must be upgraded to `confirmed` before being
  treated as reliable.

## Acceptance criteria

(Restated from the original request, mapped onto this design.)

1. A new guest can be discovered from an episode title/notes without
   re-fetching a transcript (Phase A).
2. A canonical person profile is created automatically if the guest is
   new, marked `identity_confidence: likely`/`uncertain` until
   confirmed.
3. A returning guest resolves to their existing `people/*.yaml` record
   via name/alias matching, never duplicated.
4. Each appearance is a separate record under
   `sources/<person>/<episode-slug>/`, linked to one shared
   `sources/episodes/<episode-slug>.yaml`.
5. Statements remain tied to an exact appearance, with
   `speaker_confidence` recording attribution certainty in the absence
   of true diarization.
6. Verified statements remain retrievable across every appearance by a
   person, per SKILL.md's existing longitudinal-reconstruction rule.
7. `scripts/generate_profiles.py` produces a derived, regeneratable
   profile per person from `verified` statements only.
8. Every profile line points back to a statement id.
9. Direct statements vs. synthesis stay distinguished exactly as
   SKILL.md already requires — this spec doesn't relax that rule.
10. Apparent position changes are worded cautiously per SKILL.md's
    existing language rules, applied to the new "Evolution" profile
    section.
11. Hosts are `role: host` people like any other — never conflated
    with `role: guest` statements from the same episode.
12. Cross-person comparison continues to be assembled from
    `verified` statements at query time (already true today; unchanged
    by this spec).
13. Editing/rejecting/reassigning a statement is reflected the next
    time `generate_profiles.py` runs — nothing is cached beyond that.
14. No profile content exists without a statement id it traces back
    to.

## Open risks / explicitly deferred

- **Scale of Phase B.** Not scheduled here; deferred to ongoing,
  prioritized, episode-by-episode work exactly like host extraction
  was.
- **Fuzzy name matching for Phase A** is heuristic (normalized
  string/alias match) and can misfire on common names — false merges
  are worse than false splits, so ties are resolved by NOT merging
  (creating a new stub) rather than guessing, consistent with "if
  identity is uncertain, retain the uncertainty rather than guessing."
- **No real diarization** remains a standing limitation;
  `speaker_confidence` communicates that honestly rather than
  pretending otherwise.
