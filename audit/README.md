# audit/ — data audit, repairs, and the language-level classification

Everything in this folder documents how the datasets in `norm_datasets/`,
`surveyor_norms/` and `mturk_norms/` were audited, repaired and classified between
2026-08-19 and 2026-08-22. Start with **LEVELS.md** for the classification, or with
`reports/2026-08-19_data_audit.md` for the data-quality story.

## Current state (use these)

| file | what it is |
|---|---|
| [`dataset_levels.csv`](dataset_levels.csv) | **The classification.** One row per dataset (291): id, collection, paths, `level`, `sublevel`, `decided_by`, `rationale`, and the blind-verification columns. |
| [`CODEBOOK.md`](CODEBOOK.md) | The scheme: six levels (subword → lexical semantics → syntax → sentence semantics → pragmatics → discourse) + the residual `other` class, the assignment procedure, and every boundary decision. |
| [`LEVELS.md`](LEVELS.md) | The write-up: levels with their conditions and counts, and the assignment + validation procedure. |
| [`dataset_grouping.csv`](dataset_grouping.csv) / [`GROUPING.md`](GROUPING.md) | Which datasets are batches of one experiment, and which experiments belong to one project (deterministic, from stimulus overlap and metadata). |
| [`surveyor_instruction_provenance.csv`](surveyor_instruction_provenance.csv) | Per-survey split of the participant preamble into task vs procedural sentences (drives what is in each surveyor instruction file). |
| [`scripts/group_datasets.py`](scripts/group_datasets.py) | Rerunnable grouping script. |

## reports/ — the paper trail, dated

- `2026-08-19_data_audit.md` (+ `_findings.csv`, 389 findings) — the deep audit of the
  MTurk and surveyor conversions against the raw exports, and what was repaired.
- `2026-08-21_surveyor_instructions.md` — provenance diagnosis of the surveyor
  instructions and the preamble rebuild.
- `2026-08-21_published_sets.md` — audit of the 20 published reference datasets.
- `2026-08-21_levels_v1_superseded.md` — the first classification round (superseded by
  `LEVELS.md`; kept for the record).
- `2026-08-22_merges.md` — every dataset merge, with the evidence and four caveats.

## evidence/ — machine-readable backing for the decisions

`context_probe.json` (family-level context manipulation per context+target dataset) ·
`duplicates.json` (exact and near-duplicate detection) · `merges_exact.json`,
`merges_near.json` (what was pooled into what) · `verification_pass_{0..4}.csv` and
`verification_disagreements.json` (the blind re-classification: 286/291 agreement) ·
`review_page.html` (source of the human review page, published at
https://claude.ai/code/artifact/25fc9086-64fb-417d-afdd-29e39c100eba).

## Open items

- Grouping: 34 singletons and 69 name-only groupings await collaborator confirmation;
  mapping projects → papers needs a manifest from the lab (`GROUPING.md`).
- Four merge caveats to veto or confirm (`reports/2026-08-22_merges.md`).
- Native-speaker check of the translated instruction boilerplate in the 11
  non-English datasets.
- Analysis-time caveats: `massive_mem` ↔ published-norm item overlap; L2 participants
  retained in the class-demo surveys; `missing_vp` sibling surveys have opposite
  scale polarity.
