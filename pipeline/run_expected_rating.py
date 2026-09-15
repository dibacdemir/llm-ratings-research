#!/usr/bin/env python
"""Expected ratings from option logprobs.

For every item in a task we build the prompt from the task's own instruction
file, read the model's probability of each answer option ("1".."7") off the
logits, renormalise, and record the full PMF plus its expectation.

    python pipeline/run_expected_rating.py --list
    python pipeline/run_expected_rating.py \
        --task amouyal2024_plausibility \
        --model Qwen/Qwen3-8B \
        --out runs/amouyal_qwen3-8b.jsonl

Writes <out> (one JSON object per item) and <out>.meta.json (the run's config,
including the verbatim first prompt, so a run is reproducible from its output).
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

from llm_ratings import data, prompt as prompt_mod  # noqa: E402


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--list", action="store_true",
                   help="list available tasks and exit")
    p.add_argument("--sources", default="published",
                   help="comma-separated: published,surveyor,mturk (for --list)")
    p.add_argument("--task", help="task name, e.g. amouyal2024_plausibility")
    p.add_argument("--model", help="HF model id or local path")
    p.add_argument("--out", help="output .jsonl path (overrides --result-root)")
    p.add_argument("--result-root", default="result",
                   help="write to <root>/<model name>/<task>.jsonl (default: result)")

    p.add_argument("--scale", help="override the scale, e.g. 1-7")
    p.add_argument("--option-labels",
                   help="comma-separated surface forms to score instead of the "
                        "digits, in ascending value order and one per scale "
                        "point, e.g. 'No,Yes' for a 0-1 task. The PMF still "
                        "indexes the numeric scale, so human counts stay aligned.")
    p.add_argument("--limit", type=int, help="only the first N items (smoke tests)")
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--dtype", default="bfloat16",
                   choices=["bfloat16", "float16", "float32", "auto"])
    p.add_argument("--device-map", default="auto")
    p.add_argument("--trust-remote-code", action="store_true")
    p.add_argument("--attn", default=None, help="attn_implementation, e.g. sdpa")

    p.add_argument("--placeholder-style", default="quote",
                   choices=list(prompt_mod.PLACEHOLDER_STYLES),
                   help="how the stimulus replaces <<{...}>> (default: keep <<>>)")
    p.add_argument("--suffix", default="none", choices=["none", "auto"],
                   help="append an explicit 'answer with one number' reminder")
    p.add_argument("--auto-format", action="store_true",
                   help="REMOVED. It appended a 'respond with a single number' "
                        "line whenever that raised option_mass, so models saw "
                        "different prompts and every instruction already "
                        "carries its own answer line. Errors if given.")
    p.add_argument("--system", default=None, help="optional system prompt")
    p.add_argument("--no-chat", action="store_true",
                   help="plain completion instead of the chat template (base models)")
    p.add_argument("--answer-prefix", default="",
                   help=r"text appended after the template, e.g. '\nAnswer:'")
    p.add_argument("--no-space-variant", action="store_true",
                   help="score only '1', not also ' 1'")
    p.add_argument("--overwrite", action="store_true")
    return p.parse_args(argv)


def model_slug(model):
    """'meta-llama/Meta-Llama-3.1-8B-Instruct' -> 'Meta-Llama-3.1-8B-Instruct'.

    Local paths collapse to their directory name. The full id is kept in the
    run's .meta.json, so this only has to be a readable folder name.
    """
    return os.path.basename(str(model).rstrip("/")) or "model"


def do_list(sources):
    rows = data.list_tasks(sources=tuple(s.strip() for s in sources.split(",")))
    print("%-52s %-10s %8s %8s" % ("task", "source", "items", "w/ indiv"))
    for task, source, csv_path, _instr in rows:
        try:
            items = data.load_items(csv_path)
        except Exception as exc:  # keep listing usable if one file is odd
            print("%-52s %-10s  <unreadable: %s>" % (task[:52], source, exc))
            continue
        n_ind = sum(1 for it in items if it["individual"])
        print("%-52s %-10s %8d %8d" % (task[:52], source, len(items), n_ind))


def main(argv=None):
    args = parse_args(argv)
    if args.list:
        do_list(args.sources)
        return 0
    for req in ("task", "model"):
        if not getattr(args, req):
            print("error: --%s is required (or use --list)" % req, file=sys.stderr)
            return 2
    if not args.out:
        args.out = os.path.join(args.result_root, model_slug(args.model),
                                args.task + ".jsonl")
    if os.path.exists(args.out) and not args.overwrite:
        print("error: %s exists (use --overwrite)" % args.out, file=sys.stderr)
        return 2

    loc = data.find_task(args.task)
    instructions = prompt_mod.read_instructions(loc["instructions"])
    items = data.load_items(loc["csv"], limit=args.limit)
    lo, hi = data.resolve_scale(instructions, items, override=args.scale,
                                task=args.task)
    values = list(range(lo, hi + 1))
    if args.option_labels:
        options = [s.strip() for s in args.option_labels.split(",")]
        if len(options) != len(values):
            print("error: --option-labels has %d entries but the scale has %d "
                  "points (%d-%d)" % (len(options), len(values), lo, hi),
                  file=sys.stderr)
            return 2
    else:
        options = [str(v) for v in values]
    print("task %s (%s): %d items, scale %d-%d, options %s, placeholder %s"
          % (loc["task"], loc["source"], len(items), lo, hi, options,
             prompt_mod.placeholders(instructions)))

    # torch import is deferred so that --list works without a GPU env
    from llm_ratings.hf_backend import HFRatingScorer, expected_rating, normalise

    scorer = HFRatingScorer(args.model, dtype=args.dtype, device_map=args.device_map,
                            trust_remote_code=args.trust_remote_code,
                            attn_implementation=args.attn)

    style, suffix = args.placeholder_style, (None if args.suffix == "none"
                                             else args.suffix)

    def render(it, style, suffix):
        return prompt_mod.to_model_input(
            prompt_mod.build_prompt(instructions, it["unit"], lo, hi,
                                    style=style, suffix=suffix, options=options),
            scorer.tokenizer, chat=not args.no_chat, system=args.system,
            answer_prefix=args.answer_prefix)

    if args.auto_format:
        sys.exit("--auto-format was removed (2026-09-11): the prompt is the "
                 "instruction as written, nothing appended. option_mass is "
                 "recorded per item, so a model that does not answer with a "
                 "digit shows up as low mass rather than being re-prompted.")

    texts = [render(it, style, suffix) for it in items]

    outdir = os.path.dirname(os.path.abspath(args.out))
    if outdir:
        os.makedirs(outdir, exist_ok=True)
    meta = {
        "task": loc["task"], "source": loc["source"], "csv": loc["csv"],
        "instructions_file": loc["instructions"], "model": args.model,
        "scale": [lo, hi], "options": options, "n_items": len(items),
        "chat_template": not args.no_chat, "system": args.system,
        "placeholder_style": style, "suffix": suffix or "none",
        "answer_prefix": args.answer_prefix,
        "space_variant": not args.no_space_variant,
        "dtype": args.dtype, "batch_size": args.batch_size,
        "option_token_ids": scorer.variant_ids(options, not args.no_space_variant),
        "example_prompt": texts[0] if texts else None,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(args.out + ".meta.json", "w") as fh:
        json.dump(meta, fh, indent=2)

    t0 = time.time()
    with open(args.out, "w") as fh:
        for start in range(0, len(texts), args.batch_size):
            chunk = texts[start : start + args.batch_size]
            lp = scorer.option_logprobs(
                chunk, options, with_leading_space=not args.no_space_variant)
            pmf, mass = normalise(lp)
            for j in range(len(chunk)):
                it = items[start + j]
                fh.write(json.dumps({
                    "idx": start + j,
                    "unit": it["unit"],
                    "probs": [round(float(x), 8) for x in pmf[j]],
                    "option_mass": round(float(mass[j]), 8),
                    "expected": round(expected_rating(pmf[j], values), 6),
                    "argmax": values[int(np.argmax(pmf[j]))],
                    "human_mean": it["mean"],
                    "human_n": it["n"],
                }) + "\n")
            done = min(start + args.batch_size, len(texts))
            if start == 0 or done % (args.batch_size * 20) == 0 or done == len(texts):
                rate = done / max(time.time() - t0, 1e-9)
                print("  %d/%d  (%.1f items/s)" % (done, len(texts), rate), flush=True)

    print("wrote %s  [%.1fs]" % (args.out, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
