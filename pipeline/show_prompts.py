#!/usr/bin/env python
"""Print the complete prompt, exactly as a model receives it, for every dataset.

Andrea's review asked for whole prompts to be read per dataset before a sweep,
not just spot checks, because the failures that matter are invisible in
aggregate numbers: a placeholder left unfilled, an accent stripped on the way
into the string, a scale sentence that names a different range than the data.

    python pipeline/show_prompts.py                     # every wired dataset
    python pipeline/show_prompts.py --task muraki2023_concreteness
    python pipeline/show_prompts.py --items 3 --model Qwen/Qwen2.5-7B-Instruct
    python pipeline/show_prompts.py --check             # assertions only, no text

Without --model the prompt is shown before the chat template is applied, which
is the part the instruction file controls. With --model the model's own
template is wrapped around it, which is literally what gets tokenised.
"""

import argparse
import re
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_ratings import data, prompt, task_meta  # noqa: E402

BAR = "=" * 78


EXCLUDED = {}   # task -> why it was left out of the last wired_tasks() call
WARNINGS = []   # (task, unit, why): differences worth knowing, not worth blocking


def wired_tasks(sources=("published",)):
    """Tasks that can actually be scored, in reading order."""
    out = []
    for task, source, csv_path, instr in data.list_tasks(sources=sources):
        if task in task_meta.BROKEN:
            continue
        text = prompt.read_instructions(instr)
        if len(set(prompt.placeholders(text))) != 1:
            continue
        # A dataset is scorable when a discrete scale can be pinned down, with
        # or without trial-level ratings: the aggregate-only sets still let a
        # model be compared against the published item means, which is what
        # most norming studies release. resolve_scale is the same call the
        # scorer makes, so this list cannot drift from what will actually run.
        items = data.load_items(csv_path, limit=400)
        if not items:
            continue
        try:
            data.resolve_scale(text, items, task=task)
        except ValueError:
            continue
        # Text decoded with the wrong codec would put different characters in
        # front of the model than the raters saw. Such a dataset is left out of
        # the sweep -- and named, so the omission is visible -- until the
        # collaborators repair the file, when it comes back on its own.
        bad = next((it["unit"] for it in data.load_items(csv_path)
                    if mojibake_of(it["unit"])), None)
        if bad:
            EXCLUDED[task] = "double-encoded text, e.g. %r" % bad[:50]
            continue
        out.append((task, csv_path, instr))
    # Andrea's seven levels, coarse to fine; anything else sorts last rather
    # than crashing the check that guards every sweep
    order = task_meta.LEVEL_ORDER + ["form", "semantic", "lexical"]
    def key(r):
        lv = task_meta.level_of(r[0])[0]
        return (order.index(lv) if lv in order else 99, r[0])
    return sorted(out, key=key)


def scale_of(task, csv_path, text=None):
    """(lo, hi) exactly as the scorer resolves it."""
    items = data.load_items(csv_path, limit=400)
    try:
        return data.resolve_scale(text, items, task=task)
    except ValueError:
        return (None, None)


# UTF-8 bytes that were decoded as Latin-1 leave a recognisable signature:
# a right single quote (E2 80 99) becomes "\u00e2\u0080\u0099". The C1 control
# characters in the middle never occur in real text, which makes this safe to
# detect rather than guess at.
MOJIBAKE = set("\u0080\u0081\u0082\u0083\u0084\u0085\u0086\u0087\u0088"
               "\u0089\u008a\u008b\u008c\u008d\u008e\u008f\u0090\u0091"
               "\u0092\u0093\u0094\u0095\u0096\u0097\u0098\u0099\u009a"
               "\u009b\u009c\u009d\u009e\u009f")


def mojibake_of(s):
    """The text this string should have been, or None if it looks fine."""
    if not (MOJIBAKE & set(s)):
        return None
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return "?"


def describe_non_ascii(s):
    odd = sorted({c for c in s if ord(c) > 127})
    if not odd:
        return "none (pure ASCII)"
    return ", ".join("%r U+%04X %s" % (c, ord(c), unicodedata.name(c, "?")[:24])
                     for c in odd[:8])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", help="one task name; default is every wired task")
    ap.add_argument("--sources", default="published",
                    help="published,surveyor,mturk or 'all' (default published)")
    ap.add_argument("--items", type=int, default=2,
                    help="how many stimuli to show per dataset (default 2)")
    ap.add_argument("--model", help="also apply this model's chat template")
    ap.add_argument("--style", default="quote",
                    choices=list(prompt.PLACEHOLDER_STYLES))
    ap.add_argument("--check", action="store_true",
                    help="run the assertions and print only pass/fail lines")
    args = ap.parse_args(argv)

    tok = None
    if args.model:
        # find_cache returns a cache *root*; the loader finds the snapshot
        # inside it once HF_HOME points there, which is how the scorer does it.
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        from llm_ratings import cache
        root = cache.find_cache(args.model, os.environ.get(
            "LLM_RATINGS_CACHES",
            "/home/phan3/orcd/scratch/huggingface "
            "/orcd/data/evelina9/001/USERS/phan3/hf_cache").split())
        if not root:
            sys.exit("no local cache holds %s" % args.model)
        os.environ["HF_HOME"] = root
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(args.model)

    src = ("published", "surveyor", "mturk") if args.sources == "all" else \
        tuple(x.strip() for x in args.sources.split(","))
    tasks = wired_tasks(src)
    if args.task:
        tasks = [t for t in tasks if t[0] == args.task]
        if not tasks:
            tasks = wired_tasks(("published", "surveyor", "mturk"))
            tasks = [t for t in tasks if t[0] == args.task]
        if not tasks:
            sys.exit("no wired task named %r" % args.task)

    failures = []
    for task, csv_path, instr in tasks:
        text = prompt.read_instructions(instr)
        lo, hi = scale_of(task, csv_path, text)
        items = data.load_items(csv_path)
        if not items:
            continue
        # spread the examples through the file, and make sure at least one
        # non-ASCII stimulus is shown when the dataset has any
        step = max(1, len(items) // args.items)
        picks = [items[min(i * step, len(items) - 1)]["unit"]
                 for i in range(min(args.items, len(items)))]
        odd = next((it["unit"] for it in items
                    if any(ord(c) > 127 for c in it["unit"])), None)
        if odd and odd not in picks:
            picks[-1] = odd

        meta = task_meta.meta_of(task)
        if not args.check:
            print("\n" + BAR)
            print("%s   [%s / %s]" % (task, meta["level_label"], meta["source"]))
            print("scale %s-%s   placeholder {%s}   %d items with trial data"
                  % (lo, hi, prompt.placeholders(text)[0], len(items)))
            print("non-ASCII in the instruction: %s" % describe_non_ascii(text))
            print(BAR)

        for unit in picks:
            built = prompt.build_prompt(text, unit, lo, hi,
                                        style=args.style, suffix=None)
            shown = built
            if tok is not None:
                shown = tok.apply_chat_template(
                    [{"role": "user", "content": built}],
                    tokenize=False, add_generation_prompt=True)

            # --- assertions, the reason this script exists
            problems = []
            if "<<{" in shown or "}>>" in shown:
                problems.append("a placeholder was left unfilled")
            if unit not in shown:
                problems.append("the stimulus is not present verbatim")
            if any(ord(c) > 127 for c in unit) and unit not in shown:
                problems.append("non-ASCII stimulus was altered")
            fixed = mojibake_of(unit)
            if fixed:
                problems.append("double-encoded text: reads %r, should be %r"
                                % (unit[:44], fixed[:44]))
            if str(lo) not in shown or str(hi) not in shown:
                problems.append("the prompt never names the %s-%s range" % (lo, hi))
            if tok is not None:
                back = tok.decode(tok.encode(shown, add_special_tokens=False))
                if unit not in back:
                    # Some tokenizers (Llama 3) fold a space before punctuation
                    # into the punctuation token, so "stayed ." reaches the
                    # model as "stayed." -- a formatting loss, not a content
                    # one. Recorded as a warning so it is seen; anything else
                    # missing is a real failure.
                    squash = lambda x: re.sub(r"\s+([.,!?;:])", r"\1", x)
                    if squash(unit) in squash(back):
                        WARNINGS.append((task, unit, "tokenizer drops the space "
                                         "before punctuation; model sees %r"
                                         % squash(unit)[:40]))
                    else:
                        problems.append("stimulus does not survive the tokenizer")
            if problems:
                failures.append((task, unit, problems))

            if not args.check:
                print("\n--- stimulus %r%s" % (
                    unit[:60],
                    "   (contains %s)" % describe_non_ascii(unit)
                    if any(ord(c) > 127 for c in unit) else ""))
                print(shown)
                print("--- end of prompt ---")
                if problems:
                    print("!! " + "; ".join(problems))

    print("\n" + BAR)
    if WARNINGS:
        seen = {}
        for t, u, why in WARNINGS:
            seen.setdefault(t, (u, why))
        print("warnings (scored anyway):")
        for t, (u, why) in sorted(seen.items()):
            print("  %-46s %s" % (t[:46], why))
        print()
    if EXCLUDED:
        print("left out of the sweep until the data is repaired:")
        for t, why in sorted(EXCLUDED.items()):
            print("  %-46s %s" % (t[:46], why))
        print()
    if failures:
        print("FAILED on %d prompt(s):" % len(failures))
        for task, unit, probs in failures:
            print("  %-46s %r: %s" % (task[:46], unit[:26], "; ".join(probs)))
        return 1
    print("%d datasets, %d prompts each: placeholder filled, stimulus verbatim, "
          "scale named%s." % (len(tasks), args.items,
                              ", survives the tokenizer" if tok else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
