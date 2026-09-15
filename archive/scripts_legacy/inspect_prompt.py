#!/usr/bin/env python
"""What does the model actually want to say, and which prompt format fixes it?

`option_mass` near zero means the model's first token is not a digit, so the
renormalised PMF is a rescaled tail and cannot be trusted. This prints, for a
few items and several prompt formats, the top-k next tokens with their
probabilities and the resulting option mass — so the format choice is made from
evidence instead of taste.

    python scripts/inspect_prompt.py --task dentella2023_grammaticality \
        --model meta-llama/Meta-Llama-3.1-8B-Instruct
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
import torch  # noqa: E402

from llm_ratings import data, prompt as P  # noqa: E402

# (label, placeholder_style, suffix, answer_prefix)
VARIANTS = [
    ("as-is", "angle", None, ""),
    ("quote", "quote", None, ""),
    ("+suffix", "angle", "auto", ""),
    ("+prefix 'Rating:'", "angle", None, "Rating:"),
    ("+prefix 'Rating: '", "angle", None, "Rating: "),
    ("+suffix +prefix", "angle", "auto", "Rating:"),
    ("quote+suffix+prefix", "quote", "auto", "Rating:"),
]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--n-items", type=int, default=3)
    ap.add_argument("--topk", type=int, default=8)
    ap.add_argument("--scale")
    ap.add_argument("--dtype", default="bfloat16")
    args = ap.parse_args(argv)

    loc = data.find_task(args.task)
    instr = P.read_instructions(loc["instructions"])
    items = data.load_items(loc["csv"], limit=args.n_items)
    lo, hi = data.resolve_scale(instr, items, override=args.scale)
    options = [str(v) for v in range(lo, hi + 1)]

    from llm_ratings.hf_backend import HFRatingScorer, normalise

    sc = HFRatingScorer(args.model, dtype=args.dtype)
    tok = sc.tokenizer

    print("task %s  scale %d-%d  options %s" % (args.task, lo, hi, options))
    print("model %s\n" % args.model)

    for label, style, suffix, prefix in VARIANTS:
        texts = [
            P.to_model_input(
                P.build_prompt(instr, it["unit"], lo, hi, style=style, suffix=suffix),
                tok, chat=True, answer_prefix=prefix)
            for it in items
        ]
        lp = sc.option_logprobs(texts, options)
        pmf, mass = normalise(lp)
        vals = np.arange(lo, hi + 1)

        with torch.inference_mode():
            enc = tok(texts, return_tensors="pt", padding=True,
                      add_special_tokens=False)
            enc = {k: v.to(sc.device) for k, v in enc.items()}
            logits = sc.model(**enc).logits[:, -1, :].float()
            probs = torch.softmax(logits, dim=-1)
            top = torch.topk(probs, args.topk, dim=-1)

        print("=" * 78)
        print("%-22s  tail=%r" % (label, texts[0][-42:]))
        print("=" * 78)
        for i in range(len(items)):
            toks = [(tok.decode([t]), float(p))
                    for t, p in zip(top.indices[i].tolist(), top.values[i].tolist())]
            print("  item %d  mass=%.4g  E=%.3f  human=%.3f"
                  % (i, mass[i], float(np.dot(pmf[i], vals)),
                     items[i]["mean"] if items[i]["mean"] is not None else float("nan")))
            print("    top: " + "  ".join("%r %.3f" % (t, p) for t, p in toks))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
