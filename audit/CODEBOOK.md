# Language-level codebook (v4, final — 2026-08-22; counts refreshed after blind verification)

Every dataset is assigned to exactly one **level** (and a sublevel where the level has
them) according to **what participants were asked to rate** and **what varies across
the items** — never according to the dataset's name or the researcher's folder name.
The levels form the ladder used for reporting:

**subword → lexical semantics → syntax → sentence semantics → pragmatics → discourse**

plus one auxiliary class, `other`, for rating variables that are not a linguistic
level (sublevels `lexical` and `sentence` record where the rated unit sits).

## Assignment procedure (applied in this order)

1. **What is the rated unit?** A sub-lexical form or nonword → `subword`. A word or
   short expression → step 2. A sentence, utterance, or passage → step 3.
2. **Word-level: is the rated dimension a property of the word's meaning?** Yes →
   `lexical_semantics` (sublevel by dimension type). No (age of acquisition,
   familiarity, cloze predictability, lexical-choice naturalness) → `other/lexical`.
3. **Sentence-level: what varies across items, and what is the judgment about?**
   - Structure varies and the judgment is well-formedness / naturalness /
     acceptability / comprehensibility → `syntax`.
   - Propositional content varies and the judgment is about that content
     (plausibility, likelihood, truth, sense; sentence-level affect; what the
     sentence makes you think of) → `sentence_semantics`.
   - The judgment is about interpretation beyond the literal content of one sentence
     or utterance (who a pronoun refers to; whether a presupposition is satisfied or
     a context is needed; literalness; the speaker's intended meaning; felicity of an
     utterance in a described situation) → `pragmatics`.
   - The judgment depends on the relation between the target and OTHER sentences
     → `discourse` (step 4 decides for context+target designs).
   - The rated variable is not a linguistic level (sentence frequency / likelihood of
     encounter, cloze predictability, word length in context) → `other`.
4. **Context rule (context + target designs).** Look at how context is manipulated
   *across items*, not at whether a context is present:
   - **context matters** — the same target occurs under different contexts, or
     context variants are crossed with target variants inside item families
     (givenness × word order, antecedent set × ellipsis, clause order × pronoun,
     presupposition trigger × prior sentence, dialogue turn × reply) → `discourse`;
   - **context is inert** — every item has a lead-in but it is constant within
     families and only the target varies → classify the target on its own merits
     (step 3).
5. **Naturalness is a question, not a level.** "How natural does the sentence
   sound?" is `syntax` only when items vary in structure; when items vary in meaning
   (semantic/animacy anomalies, malapropisms, personification) it is
   `sentence_semantics/plausibility`; when the situation/utterance fit is judged it
   is `pragmatics`.

## Levels and conditions

### subword (7)
The rating is driven by word **form**. Includes wordlikeness of nonwords
("how natural does the made-up word sound as a possible English word?"), affective
responses to pseudowords (the stimuli have no meaning), iconicity of real words
(sound–meaning resemblance is a property of the form), and spelling-to-sound
transparency/difficulty.

### lexical_semantics (59) — sublevels
A property of the **meaning** of an individual word or short expression.
- `affective`: valence/pleasantness, arousal, dominance, emotion-relatedness.
- `perceptual_motor`: concreteness, imageability, sensory strength by modality,
  motor/effector strength, body–object interaction, size of the referent.
- `conceptual`: any other meaning dimension (socialness, motivation, cognition,
  animacy, verb causality, semantic-feature dimensions such as morality, time,
  space, quantity, social interaction, thought).

### syntax (100)
Well-formedness / naturalness / acceptability / grammaticality / comprehensibility of
a sentence or phrase where what varies across items is **structure**: word order,
agreement, islands, clefting/topicalization, argument alternations, ellipsis and
antecedent-contained deletion in isolation, multiple-wh, complement frames
(subcategorization), center-embedding depth, word-order corruptions, disfluency
placement. Includes context+target designs whose context is inert (step 4), and
within-sentence pronoun *binding* items (the `p_p` donkey-anaphora series, by
Andrea's decision).

### sentence_semantics (45) — sublevels
The judgment is about the **content** of a sentence, not its structure.
- `plausibility`: plausibility / likelihood of the described event / truth /
  sense; "naturalness" sets whose items vary in meaning; comparative illusions.
- `affective`: valence / arousal of sentences.
- `conceptual_content`: what the sentence(s) evoke — mental states, physical
  objects, places/scenes, imageability — rated on single sentences or on pairs
  treated as one unit.

### pragmatics (16)
Interpretation **beyond the literal propositional content of one sentence or
utterance**, without reference to other sentences of a text: pronoun reference
strength driven by verb implicit causality and connective (6), presupposition /
"does this sentence need a context?" (2), literalness of a reply (1), confidence in
the speaker's intended meaning of a misheard sentence (1), agreement with an
inference drawn from a two-sentence passage (1), and felicity of an utterance in a
described situation (5: the situation is constant across items, so the construct is
speech-act felicity rather than well-formedness).

### discourse (47)
The judgment **depends on the relation between the target and other sentences**:
coherence / connectedness / causal relation between S1 and S2; cross-sentence
presupposition ("again", "too", definiteness) and VP-ellipsis / anaphora felicity;
connective and clause-order manipulations across a passage; likelihood of a causal
statement given a passage; and context+target designs where the context is
manipulated in relation to the target (givenness × dative/locative order, antecedent
set × ACD ellipsis, dialogue context × reply).

### other (17) — sublevels `lexical` / `sentence`
Rating variables that are **not a linguistic level**; kept in the collection but
outside the ladder. Sublevel `lexical` (11): age of acquisition (4),
familiarity (5), cloze predictability of a word in context (1), and one naturalness
set whose items vary only in lexical choice (abbreviation vs full form). Sublevel
`sentence` (6): subjective sentence frequency / likelihood of
encountering the sentence (2), likelihood or plausibility of noun-phrase preambles
built for agreement and preposition-choice experiments (3), and one naturalness set
whose items vary only in the length of a word inside the sentence (1).


## Boundary decisions (recorded so they can be revisited)
- Single-sentence presupposition → pragmatics; two-sentence presupposition whose
  felicity depends on the prior sentence → discourse (context rule).
- Within-sentence pronoun *interpretation* driven by verb semantics → pragmatics;
  within-sentence pronoun *binding* (donkey anaphora) → syntax.
- Same stimuli rated on different dimensions are different datasets (e.g. the five
  `massive_mem` dimensions, the `discourse_*` constructs); `discourse_*` is a project
  name — its content ratings are sentence_semantics, only the coherence/causality/
  connectedness lists are discourse.
- Pseudoword valence and iconicity → subword (form-driven), per Andrea's decision.
- `lexical_other` was merged into `other` on 2026-08-22 (Andrea): one residual class,
  with `lexical`/`sentence` sublevels preserving where the rated unit sits.
- Aggregate-only and continuous-scale norms are full members of their level; the
  level says what was rated, not how the pipeline scores it.

## Resolutions after the blind verification pass (2026-08-22)
- `50_sentences_with_2_comp_qs_plus_rating`: the question asks the likelihood of the
  described event → sentence_semantics/plausibility, even though some items are
  voice/order variants of each other.
- `depth_charge_with_noise`: depth-charge (comparative-illusion) items with noise
  corruptions on ~28% of items → sentence_semantics/plausibility (dominant construct).
- `noisy_channel_acceptability_1/2`: one noisy-channel design mixing word-order and
  insertion/deletion corruptions (dominant) with role reversals → syntax.
- `agreement_norming_nov_17/18`: likelihood of noun-phrase preambles built for
  agreement experiments → other (Andrea's decision; a blind classifier read them as
  syntax).
