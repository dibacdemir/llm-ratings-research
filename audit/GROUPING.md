# Dataset grouping: batches vs experiments vs projects (2026-08-21)

Deterministic reconstruction, from metadata only (no LLM classification), of how the
167 `mturk_norms` and 100 `surveyor_norms` datasets relate. Script:
`audit/scripts/group_datasets.py` (rerunnable; needs the extracted raw MTurk export
for batch dates). Table: [`dataset_grouping.csv`](dataset_grouping.csv) — one row
per dataset with `experiment_group`, `project_group`, the evidence, and
`ask_collaborator`.

## Levels and rules

- **Experiment group (E)** = batches, Latin-square lists, waves, or re-runs of ONE
  experiment. Merged when (a) ≥80% of the smaller dataset's stimuli occur in the
  other AND same dimension/prompt AND same scale, or (b) same project token, same
  dimension and scale, and names differing only by a list/set/wave/version/rerun/
  date suffix (Latin-square lists are stimulus-disjoint by design, so names carry
  that information).
- **Project group (P)** = different experiments of ONE study/paper. Merged when in
  the same E, or ≥80% shared stimuli rated on a *different* dimension (same
  materials, another rating), or the same project token (first non-generic token of
  the dataset name; surveyor additionally requires the same owner account).
- Weak stimulus overlap (20–80%) is only *reported* (`shares_stimuli_weakly_with`),
  never merged: labs reuse filler sentences across unrelated studies.
- **Confidence**: `high` = stimulus-backed; `medium (names only)`; `singleton`.
  Groups are transitive closures, so long chains (e.g. the 12 `lb` surveys) should
  be read as "linked step by step", not "identical throughout".

## Result

| collection | datasets | experiments (multi-dataset) | projects (multi-dataset) | stimulus-backed | names-only | singletons |
|---|---|---|---|---|---|---|
| mturk | 167 | 85 (35) | 51 (28) | 99 | 45 | 23 |
| surveyor | 100 | 45 (21) | 28 (17) | 65 | 24 | 11 |

Largest projects — MTurk: **ACD/Hackl** (21 datasets, 11 experiments: the
`acd_project_*`, `presup_survey_*`, `sentence_naturalness_survey_acd_*` families —
the July-2012 presupposition surveys and the Nov-2012 ACD experiments rate the SAME
sentences on different scales), **massive_mem** (20 = 5 dimensions × {2013, 2013_end,
2014, 2014_end}; 2013 and 2014 are DIFFERENT word lists, the 5 dimensions share one
list), **lb** (12 iterations), **verb causality** (5 list versions v3o1–v3o4 + MK),
**pronouns_following_verbs** (9 = 6 variants, 3 with re-runs), **P&P** (8),
**cul_jack/2wh_3wh** (5), **richard_islands** (5). Surveyor: **discourse** (41 = 12
experiments: 4 constructs × singles/pairs × 4 or 2 lists, plus coherence/causality/
connectedness lists — identical sentence lists rated on different dimensions),
**clefting** (5), **can_noncan/susan_canonicity** (5 re-runs), **constituency/
topicalization** (5), **huang** (6 sets), the three **9.59 replication** surveys
that share stimuli, the class demos (identical stimuli 2025/2026).

## Facts worth telling collaborators (found from stimulus identity, not names)

- `verb_particle_ratings` has the SAME items as `sentence_naturalness_survey_feb_16_1_2012_60_items`
  and `..._may_1_2011_64_items` (containment 0.99/1.00) — one experiment under three names.
- `presup_survey_1/2/3_acd_july_2012` share 100% of their sentences with
  `acd_project_expt_23/24/45` and the `hackl` naturalness sets (different rating scales).
- `2wh_3wh_sentence_naturalness_survey_april_2011` is a strict subset (100%) of
  `cul_jack_sentence_naturalness_survey_april_2010`.
- `sentence_naturalness_survey_for_formal_link` = 96% of `p_p_..._june_2013_v3`.
- `reasoning_and_language_tasks` and `social_interaction_and_language_tasks`
  (TALKATIVE PIGEON) rate the same sentences.
- `chomsky_items_1` and `quantitative_syntax_survey` share 91% of passages.
- Surveyor: `constituency_tests` ≡ `topicalization_e2` (identical 48 items);
  `class_demo` ≡ `demo_9_59_2025` ≡ `demo_9_59_2026`; `base_acceptability_0908` ≈
  `_0911` (96%); `of_acceptability_2` shares ≥80% of its items with the clefting series.
- Token collisions to override if wrong: `verb_particle_ratings` was joined to the
  verb-*causality* project only by the token "verb"; `jkm` vs `jk` are treated as
  different researchers.

## What only collaborators can answer

1. The **23 MTurk + 11 surveyor singletons** (`confidence=singleton` in the CSV):
   which project/paper each belongs to.
2. The **45 + 24 names-only groupings** (`medium`): confirm that name families like
   `for_lb_*`, `for_jk_*`, `pronouns_following_verbs_*`, `huang_response_*`,
   `lexical_frame_*` are one project and which members are re-runs vs new experiments.
3. Which projects map to which **papers** (the export has no manifest linking
   folders to publications); the CSV's `project_group` is the unit to label.
