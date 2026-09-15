"""One place that says, for a task: where it came from and what it probes.

Before this, build_explorer_data.py carried a hand-written dict and
build_report_data.py carried a substring-matching function, and the two
disagreed. Both now read from here.

Two independent facts are recorded:

  source  where the ratings came from -- 'published' (a released norming
          study), 'surveyor' or 'mturk' (collected by the lab). Read from
          data/<level>/<task>/metadata.json, never guessed.

  level   which level of language the task asks about:
            form      orthography and phonology -- how a word is spelled or
                      sounds, not what it means
            syntax    whether a sentence is well formed
            semantic  the meaning of a sentence or its fit to a context
            lexical   a property of a single word or concept

The level of a published task is stated explicitly below, each one checked
against the instructions the raters actually saw. Anything not listed falls
back to a keyword guess, which is marked as such so the page can show that it
was inferred rather than confirmed.
"""

import functools

FORM, SYNTAX, SEMANTIC, LEXICAL = "form", "syntax", "semantic", "lexical"

# Andrea's scheme (audit/CODEBOOK.md), coarse to fine, plus the residual class.
# data/<level>/ uses these keys; the labels are what the page shows.
LEVEL_ORDER = ["subword", "lexical_semantics", "syntax", "sentence_semantics",
               "pragmatics", "discourse", "other"]
LEVEL_LABEL = {
    "subword": "Subword",
    "lexical_semantics": "Lexical semantics",
    "syntax": "Syntax",
    "sentence_semantics": "Sentence semantics",
    "pragmatics": "Pragmatics",
    "discourse": "Discourse",
    "other": "Other",
    # the older four-way scheme, kept so old runs still label
    FORM: "Form", SYNTAX: "Syntax", SEMANTIC: "Semantics", LEXICAL: "Lexical",
}
SUBLEVEL_LABEL = {
    "affective": "affective", "perceptual_motor": "perceptual / motor",
    "conceptual": "conceptual", "plausibility": "plausibility",
    "conceptual_content": "conceptual content", "lexical": "lexical",
    "sentence": "sentence",
}

LEVEL_BLURB = {
    FORM: "how a word is spelled or pronounced",
    SYNTAX: "whether a sentence is well formed",
    SEMANTIC: "the meaning of a sentence, or its fit to a context",
    LEXICAL: "a property of a single word or concept",
}

# Every published task that can be scored, with the level each one probes.
# The gloss is what the raters were asked, in short.
PUBLISHED = {
    "edwards2024_spelling_to_pronunciation_transparency": (
        FORM, "spelling-to-pronunciation transparency",
        "whether the word is pronounced the way its spelling suggests"),

    "mk_grammaticality_study_7_20":
        "254 of 1,524 stimuli carry a space before the final punctuation "
        "(\"stayed .\"). Llama-3 tokenizers fold that space into the "
        "punctuation token, so those models see \"stayed.\"; Qwen keeps the "
        "space. A formatting difference between models on this dataset, not "
        "a content one.",
    "verb_causality_study_syntax_ratings_mk_april_2010":
        "124 of 653 stimuli carry a space before the final punctuation. "
        "Llama-3 tokenizers fold it into the punctuation token; Qwen keeps it. "
        "A formatting difference between models, not a content one.",
    "dentella2023_grammaticality": (
        SYNTAX, "grammaticality",
        "is this sentence grammatically correct in English"),

    "amouyal2024_plausibility": (
        SEMANTIC, "plausibility",
        "how plausible the described situation is"),
    # devarda2023_predictability is deliberately absent from PUBLISHED and is
    # listed in BROKEN below: its instruction file is the only one of the 64
    # with two different fields, and the released CSV carries only the target
    # word, so the sentence fragment that defines the task cannot be supplied.

    "diveica2023_socialness": (
        LEXICAL, "socialness",
        "how much the word's meaning involves social interaction"),
    "muraki2023_concreteness": (
        LEXICAL, "concreteness",
        "whether the expression refers to something experienced through the senses"),
    "giurgea2025_motivation": (
        LEXICAL, "motivation",
        "how motivating the thing the word refers to feels"),
    "gatti2024_pseudoword_valence_intuitive": (
        FORM, "pseudoword valence, first reaction",
        "how positive or negative a made-up word feels on sight"),
    "gatti2024_pseudoword_valence_semantic_task": (
        FORM, "pseudoword valence, meaning-based",
        "how positive or negative a made-up word feels after considering it"),
}
# lancaster2020 is one norming study asking the same word set about eleven
# different perceptual and motor channels, so they share a level and differ
# only in the channel named in the gloss.
for _chan, _gloss in [
        ("auditory", "hearing"), ("gustatory", "taste"), ("haptic", "touch"),
        ("interoceptive", "sensations inside the body"),
        ("olfactory", "smell"), ("visual", "sight"),
        ("foot_leg", "the foot or leg"), ("hand_arm", "the hand or arm"),
        ("head", "the head (excluding mouth)"), ("mouth", "the mouth"),
        ("torso", "the torso")]:
    PUBLISHED["lancaster2020_" + _chan] = (
        LEXICAL, "sensorimotor: " + _chan.replace("_", "/"),
        "how much the concept is experienced through %s" % _gloss)

# Tasks from the two collected-here sets that have been scored so far.
# huang_response_* is six sibling stimulus sets asking the same question, so the
# set name has to stay in the label or they collapse into one another.
COLLECTED = {}
for _set in ["set1a", "set1b", "set2a", "set2b",
             "set2a_declaratives", "set2b_declaratives"]:
    COLLECTED["huang_response_" + _set] = (
        SYNTAX, "acceptability, %s" % _set.replace("_", " "),
        "how natural the sentence sounds")

# Caveats that change how a number should be read, but not whether it is
# correct. Surfaced next to the task on the page so a reader cannot miss them.
NOTES = {
    "edwards2024_spelling_to_pronunciation_transparency":
        "The name says transparency but the raters were asked for difficulty: "
        "1 is easiest to sound out, 6 is hardest. A high rating therefore means "
        "LOW transparency, and a positive correlation means the model agrees "
        "about difficulty. Flagged in Andrea's 2026-08-21 audit; the data and "
        "the instruction are internally consistent and were left unchanged.",
    "muraki2023_concreteness":
        "Re-run on 2026-08-21 data: the instruction previously offered an "
        "\"I don't know the meaning\" escape option, which drew probability "
        "away from the digits. That option was removed upstream.",
    "gatti2024_pseudoword_valence_intuitive":
        "The raters did best-worst scaling, so the published human column is a "
        "0-1 preference score, not a rating on this 1-9 scale. Rankings can be "
        "compared across the two paradigms; the means cannot, and the "
        "distribution shown is the model's alone.",
    "gatti2024_pseudoword_valence_semantic_task":
        "The raters did best-worst scaling, so the published human column is a "
        "0-1 preference score, not a rating on this 1-9 scale. Rankings can be "
        "compared across the two paradigms; the means cannot, and the "
        "distribution shown is the model's alone.",
    "mk_grammaticality_study_7_20":
        "254 of 1,524 stimuli carry a space before the final punctuation "
        "(\"stayed .\"). Llama-3 tokenizers fold that space into the "
        "punctuation token, so those models see \"stayed.\"; Qwen keeps the "
        "space. A formatting difference between models on this dataset, not "
        "a content one.",
    "verb_causality_study_syntax_ratings_mk_april_2010":
        "124 of 653 stimuli carry a space before the final punctuation. "
        "Llama-3 tokenizers fold it into the punctuation token; Qwen keeps it. "
        "A formatting difference between models, not a content one.",
    "dentella2023_grammaticality":
        "A 0/1 scale with 80 items, so its correlations carry much wider "
        "uncertainty than the 1000-item tasks and should not be ranked "
        "alongside them.",
}


# Tasks that must not be scored with this pipeline, and why. build_* skip them
# so a run that is already on disk cannot reach a page by accident.
BROKEN = {}

_GUESS = [
    (SYNTAX, ("grammatic", "acceptab", "natural", "wellformed")),
    (SEMANTIC, ("plausib", "predictab", "coheren", "sensib", "entail")),
    (FORM, ("spelling", "pronunc", "orthograph", "phonolog", "iconic",
            "pseudoword")),
]


def level_of(task):
    """Return (level, confirmed). confirmed is False when it was inferred.

    The level comes from data/<level>/<task>/metadata.json, i.e. from Andrea's
    dataset_levels.csv, whenever that tree exists; the hand-written tables
    below are only the fallback for a checkout without it."""
    from llm_ratings import data as _d
    m = _d.task_metadata(task)
    if m.get("level"):
        return m["level"], True
    for table in (PUBLISHED, COLLECTED):
        if task in table:
            return table[task][0], True
    t = task.lower()
    for level, keys in _GUESS:
        if any(k in t for k in keys):
            return level, False
    return LEXICAL, False          # the large majority of norming tasks


def short_of(task):
    """The rating dimension alone, e.g. 'socialness'."""
    for table in (PUBLISHED, COLLECTED):
        if task in table:
            return table[task][1]
    name = task.split("_", 1)[-1] if "_" in task else task
    return name.replace("_", " ")


def gloss_of(task):
    """What the raters were asked, in one phrase; '' when not recorded."""
    for table in (PUBLISHED, COLLECTED):
        if task in table:
            return table[task][2]
    return ""


def label_of(task):
    """'diveica2023 · socialness' -- study on the left, dimension on the right."""
    study = task.split("_", 1)[0] if "_" in task else task
    return "%s · %s" % (study, short_of(task))


@functools.lru_cache(maxsize=1)
def _sources():
    from llm_ratings import data
    out = {}
    for task, source, _csv, _instr in data.list_tasks(
            sources=("published", "surveyor", "mturk")):
        # a name can exist under more than one source; published wins, since
        # that is the released version of the norms
        if task not in out or source == "published":
            out[task] = source
    return out


def source_of(task):
    """'published' | 'surveyor' | 'mturk' | '' -- read from the data folders."""
    try:
        return _sources().get(task, "")
    except Exception:
        return "published" if task in PUBLISHED else ""


def meta_of(task):
    from llm_ratings import data as _d
    m = _d.task_metadata(task)
    level, confirmed = level_of(task)
    return {"task": task,
            "sublevel": m.get("sublevel"),
            "sublevel_label": SUBLEVEL_LABEL.get(m.get("sublevel") or "", m.get("sublevel")),
            "level_decided_by": m.get("level_decided_by", ""),
            "level_rationale": m.get("level_rationale", ""),
            "n_items": m.get("n_items"), "n_ratings": m.get("n_ratings"),
            "ratings_per_item": [m.get("ratings_per_item_min"),
                                 m.get("ratings_per_item_median"),
                                 m.get("ratings_per_item_max")],
            "has_individual_ratings": m.get("has_individual_ratings"),
            "merged_from": m.get("merged_from", []),
            "language": m.get("language", ""),
            "label": label_of(task),
            "short": short_of(task),
            "gloss": gloss_of(task),
            "level": level,
            "level_label": LEVEL_LABEL.get(level, level),
            "level_confirmed": confirmed,
            "note": NOTES.get(task, ""),
            # split-half, Spearman-Brown; pipeline/human_reliability.py
            "human_reliability": m.get("human_reliability") or {},
            "source": m.get("source") or source_of(task)}
