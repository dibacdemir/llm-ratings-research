# Language-level assignment of all datasets — final (2026-08-22)

**Deliverables**
- [`dataset_levels.csv`](dataset_levels.csv): one row per dataset (id, collection,
  csv_path, instruction_path, `level`, `sublevel`, `decided_by`, `rationale`,
  `blind_verification_level`, `blind_agrees`, `note`). 291 datasets after the
  2026-08-22 merges (`reports/2026-08-22_merges.md`).
- [`CODEBOOK.md`](CODEBOOK.md): the six levels and the residual `other` class, the assignment procedure, the conditions for each level, and every
  boundary decision.

## The levels (conditions in one line each; full text in the codebook)

| level | condition | n | published / surveyor / mturk |
|---|---|---|---|
| subword | rating driven by word FORM (nonword wordlikeness, pseudoword valence, iconicity, spelling–sound) | 7 | 5 / 0 / 2 |
| lexical_semantics | a property of the MEANING of a word/short expression (affective · perceptual_motor · conceptual) | 59 | 41 / 0 / 18 |
| syntax | well-formedness/naturalness/comprehensibility judged on a sentence whose STRUCTURE varies across items (incl. inert-context designs, within-sentence binding) | 100 | 2 / 36 / 62 |
| sentence_semantics | judgment about the CONTENT of a sentence (plausibility · affective · conceptual_content) | 45 | 8 / 27 / 10 |
| pragmatics | interpretation beyond literal content within ONE sentence/utterance: reference resolution, presupposition/context need, literalness, intended meaning, felicity in a situation | 16 | 0 / 0 / 16 |
| discourse | judgment depends on the relation between the target and OTHER sentences (coherence, cross-sentence presupposition/anaphora, context manipulated against the target) | 47 | 0 / 24 / 23 |
| other (sublevels `lexical` / `sentence`) | rating variable that is not a linguistic level: age of acquisition, familiarity, cloze predictability, lexical choice; sentence frequency, NP-preamble likelihood, word length in context | 17 | 8 / 1 / 8 |

Sublevels: other/lexical: 11; other/sentence: 6; lexical_semantics/affective: 16; lexical_semantics/conceptual: 12; lexical_semantics/perceptual_motor: 31; sentence_semantics/affective: 2; sentence_semantics/conceptual_content: 29; sentence_semantics/plausibility: 14.

The two rules that do most of the work: **naturalness is a question, not a level**
(classify by what varies across items), and the **context rule** for context+target
designs (context manipulated across item families → discourse; context inert →
the target's own level).

## Assignment and validation procedure

1. **Inventory.** Every dataset file in the repo (published norms, surveyor, MTurk),
   each with its instruction file; identical-item/identical-instruction duplicates
   and near-duplicate batches were merged first (`reports/2026-08-22_merges.md`).
2. **Two independent first-pass classifications** (Sonnet agents, different batch
   partitions), each reading the full instruction and the items — never the name —
   with a codebook (v1) that required flagging borderline cases. Class agreement
   94%; 125 datasets flagged or disputed.
3. **Reviewer pass (Claude Fable).** Every flagged/disputed dataset read against the
   items; recurring paradigms grouped into policy families.
4. **Andrea's decisions** on the policy families (context+target designs,
   cross-sentence relations, non-meaning variables, form–meaning cases,
   naturalness-with-meaning-variation), on individual cases through a review page
   showing each dataset's real question, scale and items, and on the addition of the
   `pragmatics` level. Decisions applied uniformly to every member of a family.
5. **Refined context rule (v3).** For every context+target dataset, items were
   clustered into families by shared context stem and the design classified by
   whether context variants are crossed with target variants
   (`evidence/context_probe.json`); 11 datasets moved discourse → syntax, 11 kept.
6. **Consistency checks.** Identical instruction text, stimulus-backed experiment
   groups (`dataset_grouping.csv`), name families and sublevel validity were checked
   mechanically; three inconsistencies were found and fixed (the `p_p` binding
   series, `acd_v1`/`acd_v6`, `noisy_channel_1`/`_2`).
7. **Blind verification (final).** Five fresh Sonnet classifiers re-labeled all 291
   datasets against the final codebook (v4) without access to any label. Level
   agreement **286/291 (98.3%)**, sublevel agreement 100% where levels agreed. The 5
   disagreements were reviewed individually and resolved (all kept; reasons in the
   `note` column and in the codebook); the blind label is retained in
   `blind_verification_level` for every dataset.

Every row's `decided_by` records which step produced the label
(`agents_consensus`, `fable_resolution`, `andrea_policy_Q1..Q5`,
`andrea_rule_context_v3`, `andrea_review_page`, `andrea_scheme_v4`,
`fable_second_look`).

## Amendment (2026-08-22, after the write-up)
`lexical_other` was merged into `other` at Andrea's request: one residual class for
non-level rating variables, with sublevels `lexical` (11) and
`sentence` (6) preserving where the rated unit sits. The scheme is now
**six levels + one residual class**. Blind-verification agreement is unchanged at
286/291 (98.3%); the five disagreements are the same ones listed above.
