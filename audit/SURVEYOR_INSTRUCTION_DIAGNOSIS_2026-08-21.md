# Surveyor instructions: complete provenance diagnosis (2026-08-21)

Prompted by a collaborator's claim that "the surveyor instructions don't come from
the demographics file — the current instruction is still kinda made up." Verdict
first, then the full accounting. Per-survey machine-readable table:
[`surveyor_instruction_provenance.csv`](surveyor_instruction_provenance.csv).

## Verdict

**Not made up — but incomplete.** Every sentence in every current instruction file
is verbatim from the raw survey export (verified exhaustively for all 100 surveys,
see §2). What the collaborator correctly identified is an **omission**: the
one-time instruction *preamble* participants read before the trials (stored in
`_demographics.csv`) was never included — and the pre-repair README's claim that
those preambles "weren't in the export" is **false** (all 100 surveys have one).
The 2026-08-20 repair inherited that false assumption without re-checking it.

## 1. What a participant actually saw, piece by piece

| Component | Raw source | In our instruction? | Should it be? |
|---|---|---|---|
| Consent statement | `_demographics.csv` `consent` row | No | No — not task content |
| Demographic questions (Prolific ID, L1, country) | `_demographics.csv` rows | No | No |
| **Instructions preamble (one-time, pre-trial)** | `_demographics.csv` `instructions` row | **No** | **Partly — the gap.** Task-content sentences yes; procedural sentences no (decided 2026-08-21) |
| Per-item question | `_stimuli.csv` `prompt` | **Yes, verbatim** (100/100 verified) | Yes ✓ |
| Response options (labels, digits, direction) | `_stimuli.csv` `options` | **Yes, verbatim** (100/100 verified) | Yes ✓ |
| Visual target marking (bold) / line breaks | HTML in `_stimuli.csv` `sentence` | Flattened; textual "Target:"-style labels retained where present | Positional wording substitutes for lost bold (7 files reworded 2026-08-21) |
| Comprehension-question trials | `_stimuli.csv` non-rating rows | No | No — not ratings |
| Item order / "fillers first" flag | `_stimuli.csv` `config`, `_parameters.json` `ordered`/`oneatatime` | No | No — presentation mechanics |
| Debriefing | `_parameters.json` `debriefing` | No | No — post-task |

The two scaffolding lines we add ("Rate on a scale from 1 to N:", "Answer with one
digit.") are ours, matching the repo-wide convention; interior scale points that
were unlabeled buttons for humans (e.g. huang's `1 - Very unnatural_2_3_4 -
Neutral_5_6_7 - Very natural`) are labeled only at the anchors, faithfully.

## 2. Verbatim verification (the positive claim)

Bulk check across all 100 surveys (not samples): the instruction's question line
appears verbatim in the survey's `prompt` column and every stated scale label
appears verbatim in its `options` — **100/100 pass on both**. Nine files carry
minimal, documented layout rewords ("above"→"below", "bolded"→"final/second
sentence" — the stimulus sits below our question and bold is not rendered); one
survey (`missing_vp_extension_0501_final`) pools two prompt variants (documented).

## 3. The missing preamble, quantified

From the sentence-level classification of all 100 preambles (32 distinct texts):

- **60/100** surveys have at least one task-relevant preamble sentence;
  **48/100** carry substantive content absent from the current instruction.
- Content types (surveys containing each): dimension definitions 58, scale
  anchoring 49, worked examples 32, judgment guidance ("first impression") 7,
  target identification 4.
- **Strong domain asymmetry**: 46/47 `sentence_semantics` surveys are affected vs
  2/53 `syntax` (`locative_topicalization_survey`, `extension_study`). The driver
  is the discourse-construct family (~32 files), whose preambles carry full
  definitions *with example ratings* while the per-item prompt is one short
  question.
- The 52 remaining preambles are purely procedural (22 share the single sentence
  "Please read each sentence and then answer the question immediately following.").

## 4. Notable incidental findings

1. **Scale-polarity flip between siblings**: `missing_vp_extension` and
   `missing_vp_rereplication` run 1 = easy … 5 = hard to understand;
   `missing_vp_extension_0501_final` runs 1 = hard … 5 = easy. Each file is
   internally consistent (instruction matches its own survey), but **do not pool
   or compare these three without aligning polarity** — added to analysis caveats.
2. **Opposite epistemic framing across syntax surveys**: some preambles say "no
   right or wrong answers — use your gut reaction", others warn "there are correct
   answers for many questions" (referring to their comprehension checks) and
   threaten rejection below 75%. Worth remembering when comparing across surveys.
3. `extension_study` is the only survey whose preamble *defines* naturalness in
   prose ("how normal or typical the sentence sounds…"); none of it is in the
   current instruction — flagship example of the gap.
4. Bold-marking is described in some preambles (Chinese, Finnish) and not others;
   positional wording now substitutes where bold was the only marker.

## 5. Implementation (EXECUTED 2026-08-21, same day)

Rebuild all 100 surveyor instructions as: **verbatim preamble (minus procedural
sentences — comprehension-question mentions, attention-check warnings, payment/ID,
pacing/count lines; every trimmed sentence logged per dataset) + per-item question
+ labeled scale + "Answer with one digit." + `<<{sentence}>>`**, in the survey's
own language (native preambles exist for all non-English sets, replacing the
machine-translated boilerplate). Executed: 60 files gained their
task-content preamble; 40 procedural-only preambles left prompts unchanged; four
non-English files needed small coherence adaptations beyond the mechanical trim
(chinese_dative dangling connective + bold→target-label wording, dative_finnish
bold reference, italian ×2 label + embedded procedural clause — including one
comma→"e" grammatical repair in the Italian preamble sentence, needed after the
mid-sentence excision of "e poi rispondi alla domanda immediatamente successiva"),
all logged here and independently verified (5/6 checks full PASS; the sixth
flagged only this Italian repair as initially undocumented — now documented). `a_index.csv` gained a `preamble_included` column.

## 6. Checked and cleared

MTurk has **no analogous gap** — verified against all three wording sources for
all 167 datasets: (a) `dashboard_instructions` is empty for 166/167 (the single
non-empty one, anne_abeille, is a confirmed fuzzy-join mismatch to an unrelated
"Happy Dog" truth study and was rightly rejected); (b) none of the 17 dashboard
template families with instruction text genuinely covers any of our rating
datasets; (c) the 49 recovered local templates, including the canonical
`html_maker_rating.py` used by the bulk of the sentence surveys, contain only
consent boilerplate + on-page micro-labels ("Sentence rating:") + labeled radio
buttons — MTurk HIT pages never carried an instructional preamble. The
participant-facing task framing lived in the HIT **Title/Description**, which our
instructions DO incorporate (it grounds the dimension wording, per
`question_provenance`). Residual, already-documented caveat: the interrogative
phrasing of each MTurk question is reconstructed, because no question sentence
existed on the page — workers inferred the task from Title + scale labels. `parameters.json`, `config`,
comprehension trials, consent: all correctly excluded (see §1). The
`missing_vp` "filler" trials were verified genuinely rated (the platform labels
every widget `multiple_choice`; their options were the 5-point Likert labels).
