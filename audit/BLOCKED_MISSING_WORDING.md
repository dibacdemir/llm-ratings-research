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

| dataset | MTurk project title |
|---|---|
| `acd_context_polly_1_nov_23_2012` † | Rating 52 English texts: PSYCHEDELIC EGGPLANT survey |
| `cul_jack_april_2012_60_short_texts_with_two_comprehension_questions_an` † | 60 short texts with two comprehension questions and a rating. CODENAME: EFFICIENT LIZARD |
| `islands_acceptability_expt_2_dec_2_2012` | Sentence comprehension: 144 complex sentences CODENAME: ROMANTIC-STRAWBERRY |
| `sentence_completions_and_islands_acceptability_expt_1_nov_13_2012` | Reasoning and sentence completions. CODENAME: ROMANTIC-STRAWBERRY |
| `richard_islands_acceptability_expt_1_april_25_2013_3` | Sentence comprehension: 1 complex sentences CODENAME: NOISY-PENGUIN |
| `richard_islands_acceptability_expt_2_april_26_2013` | Sentence comprehension: 60 complex sentences CODENAME: NOISY-PENGUIN |
| `richard_islands_acceptability_expt_4_april_26_2013_1` | Sentence comprehension: 52 complex sentences CODENAME: NOISY-PENGUIN |
| `richard_islands_acceptability_expt_5_april_27_2013_1` | Sentence comprehension: 52 complex sentences CODENAME: NOISY-PENGUIN |
| `richard_islands_acceptability_expt_6_april_28_2013_while_whq_decl` | Sentence comprehension: 52 complex sentences CODENAME: NOISY-PENGUIN |

† also needs the §2 unit re-keying (context dropped / coarse units) when repaired.

## Group 2 — no dashboard project found; need HIT HTML from local backups or researcher recall

| dataset | MTurk project title |
|---|---|
| `chomsky_items` | Very short English-language survey: 3 sentences & questions & ratings; survey code = King Chimpanzee |
| `quantitative_syntax_survey` | Brief English-language survey (37 short paragraphs) |
| `mk_alive_corpus_questionnaire` ‡ | Answer some simple questions about English sentences |
| `mk_goals_corpus_questionnaire` ‡ | Answer some simple questions about English sentences |
| `mk_thought_corpus_questionnaire` ‡ | Answer some simple questions about English sentences |
| `melissa_transitivity_semantics` | Answer some questions about simple sentences. Codename: BUTTER PECAN SMOOTHIE |
| `melissa_short_naturalness_test` | English Native Speakers: How natural are these sentences? |

‡ also needs the §2 target-NP-markup re-conversion (units currently merge two target NPs)
when repaired.

## When the wording arrives

Run the same repair as the 2026-08-20 pass for these 16: re-convert where §2 flagged unit
defects, recompute std with ddof=1, and rebuild the instruction with the recovered
question wording + all-points-labeled scale ("Answer with one digit.", correct
placeholder, no meta text). Then update `a_index.csv` (they are flagged
`status=blocked_missing_wording`) and re-run the verification checks in
`DATA_AUDIT_2026-08-19.md`.
