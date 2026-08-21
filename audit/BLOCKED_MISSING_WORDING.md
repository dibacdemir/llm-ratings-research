# RESOLVED 2026-08-21 — kept for the paper trail

> **Every dataset below was resolved on 2026-08-21** using the collaborator's
> `raw-data/RESOLVED_QUERIES.md` (verbatim dashboard scale labels): 12 were repaired —
> including `chomsky_items`, split into `chomsky_items_1`/`chomsky_items_2` (it pooled
> two studies), and, from the same response, `agreement_norming_nov`, split into
> `agreement_norming_nov_17`/`_nov_18` (two projects with two different likelihood
> scales; it was never a naturalness study). The 3 MK questionnaires and
> `melissa_transitivity_semantics` were **dropped** by Andrea's decision (the MK 1–5
> data was confidence about a separate Yes/No judgment; the Melissa rating question
> remained unidentifiable even in the dashboard). **Nothing is blocked anymore.**
> The text below is the original request, kept for provenance.

# BLOCKED: 16 MTurk datasets awaiting wording from collaborators (2026-08-20)

These 16 `mturk_norms/` datasets could **not** be fixed in the 2026-08-20 repair pass
because neither `raw-data/_WORDING.zip` nor the MTurk export contains their rating-question
wording or response-scale labels. **Their CSV + instruction files are untouched (still in
the pre-audit, known-bad state: meta-leak line, generic/unknown dimension, unlabeled
scale, ddof=0 std, and for some, the unit-definition defects listed in
`DATA_AUDIT_2026-08-19.md` §2).** Do not use them until repaired.

## Group 1 — dashboard project exists; scale/wording not captured in the export

Fixable once collaborators re-extract these projects from the MTurk Requester dashboard
(same procedure as `questionnaire_wording.csv`), or re-export `scale_catalog.json` with
untruncated per-scale project lists.

| dataset (our filename) | project name in the MTurk export / `questionnaire_wording.csv` | BatchId(s) | HITTypeId |
|---|---|---|---|
| `acd_context_polly_1_nov_23_2012` † | ACD context polly 1 nov 23 2012 | 971461–974491 (10) | 2CDCJ011K274QCBHE1X1DN46UWTCAW |
| `cul_jack_april_2012_60_short_texts_with_two_comprehension_questions_an` † | cul jack april 2012 60 short texts with two comprehension questions and a rating. CODENAME- EFFICIENT LIZARD | 770307, 770327 | 2V5WA6X3YOCC… |
| `islands_acceptability_expt_2_dec_2_2012` | Islands acceptability expt 2 Dec 2 2012 | 979297, 979442 | 2U1XMB3Q39Z0… |
| `sentence_completions_and_islands_acceptability_expt_1_nov_13_2012` | sentence completions and islands acceptability expt 1 Nov 13 2012 | 962763, 963724, 979313 | 2AOOK5UFJ51Y… |
| `richard_islands_acceptability_expt_1_april_25_2013_3` | Richard Islands acceptability expt 1 April 25 2013 3 | 1109716 | 20OCNHMVHVKC… |
| `richard_islands_acceptability_expt_2_april_26_2013` | Richard Islands acceptability expt 2 April 26 2013 | 1111340, 1112112 | 2FTLWSBRI8IU… |
| `richard_islands_acceptability_expt_4_april_26_2013_1` | Richard Islands acceptability expt 4 April 26 2013 1 | 1112428 | 2NLK9RJ85OZI… |
| `richard_islands_acceptability_expt_5_april_27_2013_1` | Richard Islands acceptability expt 5 April 27 2013 1 | 1112800 | 2NLK9RJ85OZI… |
| `richard_islands_acceptability_expt_6_april_28_2013_while_whq_decl` | Richard Islands acceptability expt 6 April 28 2013 while whq - decl | 1113164, 1118970, 1119371 | 2NLK9RJ85OZI… |

**Note on identifiers:** the participant-facing HIT `Title` is NOT a usable key — the
three MK questionnaires share one identical title, five Richard sets share the
NOISY-PENGUIN codename, and two folders share ROMANTIC-STRAWBERRY. Use the project /
folder name (the key in `questionnaire_wording.csv`) or the BatchId/HITTypeId.

† also needs the §2 unit re-keying (context dropped / coarse units) when repaired.

## Group 2 — no dashboard project found; need HIT HTML from local backups or researcher recall

| dataset (our filename) | project name in the MTurk export | BatchId(s) | HITTypeId |
|---|---|---|---|
| `chomsky_items` ¶ | Chomsky items | 200393–200413 (12) | 17N8845CWU96… + 1 more |
| `quantitative_syntax_survey` | quantitative syntax survey | 101295–101308 (10) | 73SWYMM3VVBZ… |
| `mk_alive_corpus_questionnaire` ‡ | MK - 'Alive' Corpus Questionnaire | 488203 | 2AZS8SV7WGKC… |
| `mk_goals_corpus_questionnaire` ‡ | MK - 'Goals' Corpus Questionnaire | 488598 | 2AZS8SV7WGKC… |
| `mk_thought_corpus_questionnaire` ‡ | MK - 'Thought' Corpus Questionnaire | 488599 | 2AZS8SV7WGKC… |
| `melissa_transitivity_semantics` | Melissa - Transitivity Semantics | 360710, 362625 | 1G2OJ2IFXQU1… |
| `melissa_short_naturalness_test` | Melissa- Short naturalness test | 479579–479583 (4) | 2IBNMHGYQ4J3… |

¶ **`chomsky_items` mixes two different studies** (found 2026-08-20): 6 batches ran
"Brief English-language survey: 35 questions & ratings; survey code = White Dolphin"
(37 rating columns) and 6 ran "Very short English-language survey: 3 sentences &
questions & ratings; survey code = King Chimpanzee" (3 rating columns), under two
HITTypeIds. The converted 94-unit file pools both. When wording arrives, **split this
into two datasets** rather than repairing it as one.

‡ also needs the §2 target-NP-markup re-conversion (units currently merge two target NPs)
when repaired.

## When the wording arrives

Run the same repair as the 2026-08-20 pass for these 16: re-convert where §2 flagged unit
defects, recompute std with ddof=1, and rebuild the instruction with the recovered
question wording + all-points-labeled scale ("Answer with one digit.", correct
placeholder, no meta text). Then update `a_index.csv` (they are flagged
`status=blocked_missing_wording`) and re-run the verification checks in
`DATA_AUDIT_2026-08-19.md`.
