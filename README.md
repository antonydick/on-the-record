# On the Record

A source-grounded memory layer for people who've spoken publicly.

Important things a person has said are often scattered across dozens of
long-form conversations — a passing remark 40 minutes into episode 12
that nobody would reasonably remember, mentioned nowhere else. There's
no practical way for a human, or an AI guessing from general knowledge,
to reliably reconstruct that. On the Record's answer is: capture each
thing a person says as its own small, source-grounded statement, verify
it against the recording, and let an agent assemble the picture at
query time — never inventing connections that weren't actually said.

## The primary demo: reconstructing one person across their whole corpus

> **You ask:** "How did Nikhil Kamath learn to communicate the way he
> does?"

No single appearance is "about" that question — it's not what any one
episode was pitched as. But across many interviews, on-the-record
statements on the topic might exist like this (illustrative only — this
repo doesn't contain real Nikhil Kamath data yet):

| What was said | Source | Where |
|---|---|---|
| Describes struggling with communication early on | Interview A | 42:13 |
| Mentions learning from a particular person | Interview B | 18:47 |
| Describes being coached by someone specific | Interview C | 51:02 |
| Explains how his questioning style changed | Interview D | 27:31 |

On the Record answers by pulling every `verified` statement across
*all* of that person's appearances — regardless of who interviewed
them — and presents them as a timeline, each one still attributed to
its own source and timestamp. Critically: **"Nikhil said X, Y, and Z"
is different from "the agent is inferring a progression between X, Y,
and Z."** The former is a citation. The latter is synthesis. On the
Record's data model and retrieval rules keep those two things visibly
separate — see [SKILL.md](SKILL.md).

## Two other capabilities that fall out of the same model

- **Cross-person comparison**: "What do these people agree or disagree
  on?" — e.g. what multiple experts say about a shared topic.
- **Cross-source synthesis**: patterns that only emerge by looking
  across many people's statements together.

Longitudinal reconstruction (one person, their whole corpus) is the
flagship capability; the other two are natural extensions of the same
underlying data.

## How it's organized

- `people/<id>.yaml` — minimal public identity for one person (name,
  credentials, bio). Not necessarily a domain "expert" — could be an
  interviewer, founder, scientist, investor, or anyone who's spoken
  publicly. Not a place for statements or opinions.
- `sources/<person-slug>/<interviewer-slug>/metadata.yaml` — one
  appearance by that person. The same person can have many appearance
  directories under `sources/<person-slug>/`, each with a different
  interviewer — browsing that one directory surfaces everything
  they've ever said on record, regardless of who they said it to.
- `sources/<person-slug>/<interviewer-slug>/statements.yaml` — the
  statements extracted from that specific appearance.

See `people/example-person.yaml` and `sources/example-person/` (two
appearance directories, with different interviewers) for a fully
worked, clearly-marked placeholder example of the shapes — not a real
person or real statements.

## Two things every statement keeps separate

1. **Verification** — did the person actually say this, accurately
   attributed to a specific place in the source? This is a provenance
   check. A statement only reaches `verified` once a human has
   re-checked the primary source and recorded the source URL and
   start/end timestamps.
2. **Evidence** — is the statement's content actually true? Kept as its
   own field, because a statement can be perfectly, verifiably
   attributed to a person while its content is false, contested, or
   simply unassessed.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full verification
workflow, and [SKILL.md](SKILL.md) for the retrieval rules an agent
follows when answering questions from this data.

## Validation

Every `people/*.yaml`, `sources/*/*/metadata.yaml`, and
`sources/*/*/statements.yaml` file is checked against
`schema/*.schema.yaml` on every push and pull request:

```bash
pip install -r requirements.txt
python scripts/validate.py
```

`STATS.md` is regenerated automatically on every push to `main`.
