# On the Record

Ask a cross-expert question and get an answer built from verified,
timestamped quotes — not guesses.

> **You ask:** "What do Andrew Huberman and Sahar Yousef both say about
> protecting focus during a work day?"
>
> **On the Record answers** by pulling only claims marked `verified` in
> this repository — each one checked by a human against the original
> interview at a specific timestamp — and cites exactly where each
> expert said it, so you can go watch or listen yourself.

That's the whole pitch: an AI agent shouldn't have to guess what an
expert thinks, or hallucinate a plausible-sounding paraphrase. It should
cite something a human actually confirmed was said, and show its work.

## How it's organized

- `experts/<id>.yaml` — minimal public identity for one expert (name,
  credentials, bio). Not a place for claims or opinions.
- `sources/<show-slug>/<expert-slug>/metadata.yaml` — one interview or
  appearance by that expert on a given show/podcast/publication.
- `sources/<show-slug>/<expert-slug>/claims.yaml` — the claims extracted
  from that specific appearance.

See `experts/example-expert.yaml` and `sources/example-show/example-expert/`
for a fully worked, clearly-marked placeholder example of the shapes —
not a real expert or real claims.

## Two things every claim keeps separate

1. **Verification** — did the expert actually say this, accurately
   attributed to a specific place in the source? This is a provenance
   check. A claim only reaches `verified` once a human has re-checked
   the primary source and recorded the source URL and start/end
   timestamps.
2. **Evidence** — is the claim's content actually true? Kept as its own
   field, because a claim can be perfectly, verifiably attributed to an
   expert while its content is false, contested, or simply unassessed.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full verification
workflow, and [SKILL.md](SKILL.md) for the retrieval rules an agent
follows when answering questions from this data.

## Validation

Every `experts/*.yaml`, `sources/*/*/metadata.yaml`, and
`sources/*/*/claims.yaml` file is checked against `schema/*.schema.yaml`
on every push and pull request:

```bash
pip install -r requirements.txt
python scripts/validate.py
```

`STATS.md` is regenerated automatically on every push to `main`.
