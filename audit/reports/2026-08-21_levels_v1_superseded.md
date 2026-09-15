> **Superseded on 2026-08-22 by `../LEVELS.md` / `dataset_levels.csv`** (pragmatics level added, merges applied, blind verification). Kept for the paper trail.

# Language-domain assignment of all 331 datasets (2026-08-21)

Deliverable: [`../dataset_levels.csv`](../dataset_levels.csv) — one row per dataset
(id, collection, csv_path, instruction_path, `domain`, `subdomain`, `decided_by`,
`rationale`, both classifiers' labels, `flagged`). Codebook with definitions and
decision rules: [`../CODEBOOK.md`](../CODEBOOK.md).

## Method
1. Inventory of every dataset file: 64 published (20 families), 100 surveyor, 167 MTurk.
2. Two independent Sonnet classifiers per dataset (different batch partitions), each
   reading the full instruction + items and required to flag borderline cases.
   Class agreement 310/331 (94%); 125 datasets flagged or disputed.
3. Fable review of all 125: 37 resolved under the codebook (documented per row);
   the rest grouped into 5 policy families decided by Andrea (Q1–Q5, see codebook
   v2) and applied uniformly to every member of each family (including unflagged
   siblings, for consistency).

## Result

| domain | n | published | surveyor | mturk |
|---|---|---|---|---|
| syntax | 117 | 2 | 48 | 67 |
| discourse | 79 | 0 | 24 | 55 |
| lexical_semantics | 62 (perceptual_motor 31, affective 16, conceptual 15) | 41 | 0 | 21 |
| sentence_semantics | 52 (conceptual_content 29, plausibility 15, inference_pragmatics 6, affective 2) | 8 | 27 | 17 |
| lexical_other | 10 | 5 | 1 | 4 |
| subword | 7 | 5 | 0 | 2 |
| other | 4 | 3 | 0 | 1 |

Decision provenance: 200 by classifier consensus, 37 by Fable review, 94 by
Andrea's five policy decisions (Q1 context+target 28, Q2 cross-sentence relations
37, Q3 non-meaning variables 13, Q4 form–meaning 6, Q5 meaning-varied naturalness 10).

## Notes for analysis
- The MTurk corpus is dominated by naturalness surveys; after the Q1/Q2 policies a
  third of it is `discourse` (context/situation designs, cross-sentence
  presupposition and anaphora), not `syntax`.
- The `discourse_*` surveyor family is named after its project, not its domain:
  the singles/pairs content ratings are `sentence_semantics/conceptual_content`;
  only the coherence/causality/connectedness lists are `discourse`.
- `other` holds 4 sets (tuckute2024 general/conversational frequency,
  devarda2023 predictability, word_length_context) — exclude or treat separately.
- Subdomains exist only for lexical_semantics and sentence_semantics; `syntax` and
  `discourse` could be subdivided later (e.g. syntax_in_context) from the
  `rationale` column without re-reading data.
