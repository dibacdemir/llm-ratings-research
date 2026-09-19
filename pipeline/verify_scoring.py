#!/usr/bin/env python
"""Is the logit-reading code correct? Three checks that can each fail loudly.

  1. PADDING   score every item alone (batch 1, no padding) and again in a
               padded batch. Left-padding, the attention mask and the "read
               logits at position -1" assumption are all correct only if the
               two agree to numerical precision.
  2. POSITIONS a direct forward() call does not derive position_ids from the
               attention mask, so left-padded rows get their real tokens at
               positions n_pad.. instead of 0.. . For RoPE that is a uniform
               shift and should be a no-op; this measures whether it is.
  3. PRECISION bfloat16 keeps 8 mantissa bits, so logits ~8-16 quantise in
               steps of ~0.031 and neighbouring options collapse to exactly
               equal probabilities. Compare against float32 and count the ties.

    python pipeline/verify_scoring.py --task amouyal2024_plausibility \
        --model Qwen/Qwen2.5-7B-Instruct --n-items 64
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
import torch  # noqa: E402

from llm_ratings import data, prompt as P  # noqa: E402


def count_ties(Pm, floor=1e-4):
    items = pairs = 0
    for row in Pm:
        r = [x for x in row if x > floor]
        if len(set(r)) < len(r):
            items += 1
            pairs += len(r) - len(set(r))
    return items, pairs


def score(scorer, texts, options, batch_size):
    from llm_ratings.hf_backend import normalise
    out = []
    for i in range(0, len(texts), batch_size):
        lp = scorer.option_logprobs(texts[i : i + batch_size], options)
        out.append(normalise(lp)[0])
    return np.concatenate(out, axis=0)


def report(name, A, B, vals):
    d = np.abs(A - B)
    ea = A @ vals
    eb = B @ vals
    print("  %-34s max|dP| %.2e   mean|dP| %.2e   max|dE| %.2e"
          % (name, d.max(), d.mean(), np.abs(ea - eb).max()))
    return d.max()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="amouyal2024_plausibility")
    ap.add_argument("--model", required=True)
    ap.add_argument("--n-items", type=int, default=64)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--skip-fp32", action="store_true",
                    help="skip the float32 reload (needed for big models)")
    args = ap.parse_args(argv)

    loc = data.find_task(args.task)
    instr = P.read_instructions(loc["instructions"])
    items = data.load_items(loc["csv"], limit=args.n_items)
    lo, hi = data.resolve_scale(instr, items)
    options = [str(v) for v in range(lo, hi + 1)]
    vals = np.arange(lo, hi + 1)

    from llm_ratings.hf_backend import HFRatingScorer

    print("task %s  scale %d-%d  n=%d  model %s\n"
          % (args.task, lo, hi, len(items), args.model))

    sc = HFRatingScorer(args.model, dtype="bfloat16")
    texts = [P.to_model_input(P.build_prompt(instr, it["unit"], lo, hi),
                              sc.tokenizer, chat=True) for it in items]

    print("[1] PADDING  batch=1 vs batch=%d, bfloat16" % args.batch_size)
    b1 = score(sc, texts, options, 1)
    bn = score(sc, texts, options, args.batch_size)
    pad_err = report("batch1 vs batch%d" % args.batch_size, b1, bn, vals)

    print("\n[2] POSITIONS  default cache_position vs mask-derived position_ids")
    with torch.inference_mode():
        enc = sc.tokenizer(texts[: args.batch_size], return_tensors="pt",
                           padding=True, add_special_tokens=False)
        enc = {k: v.to(sc.device) for k, v in enc.items()}
        mask = enc["attention_mask"]
        pos = (mask.cumsum(-1) - 1).clamp(min=0)
        ids = [sc.tokenizer.encode(o, add_special_tokens=False)[0] for o in options]
        lg_def = sc.model(**enc).logits[:, -1, :].float()
        lg_pos = sc.model(**enc, position_ids=pos).logits[:, -1, :].float()
        pa = torch.softmax(lg_def[:, ids], -1).cpu().numpy()
        pb = torch.softmax(lg_pos[:, ids], -1).cpu().numpy()
    pos_err = report("default vs explicit position_ids", pa, pb, vals)
    npad = int((mask == 0).sum())
    print("      (%d pad tokens in this batch; 0 pads would make this vacuous)" % npad)

    print("\n[3] PRECISION  bfloat16 vs float32")
    ti, tp = count_ties(bn)
    print("  bfloat16 exact ties: %d/%d items (%d pairs)" % (ti, len(bn), tp))
    if args.skip_fp32:
        print("  float32 comparison skipped")
        return 0
    del sc
    torch.cuda.empty_cache()
    sc32 = HFRatingScorer(args.model, dtype="float32")
    texts32 = [P.to_model_input(P.build_prompt(instr, it["unit"], lo, hi),
                                sc32.tokenizer, chat=True) for it in items]
    f32 = score(sc32, texts32, options, args.batch_size)
    ti32, tp32 = count_ties(f32)
    print("  float32  exact ties: %d/%d items (%d pairs)" % (ti32, len(f32), tp32))
    prec_err = report("bfloat16 vs float32", bn, f32, vals)
    print("  correlation of expected ratings: %.6f"
          % np.corrcoef(bn @ vals, f32 @ vals)[0, 1])

    # The decisive one: if padding is a real bug it survives the dtype change,
    # if it is bf16 rounding re-rolled by a different kernel it vanishes here.
    print("\n[4] PADDING IN FLOAT32  batch=1 vs batch=%d" % args.batch_size)
    f32_b1 = score(sc32, texts32, options, 1)
    pad32_err = report("fp32 batch1 vs batch%d" % args.batch_size, f32_b1, f32, vals)

    # External check: everything above is internal consistency. This one asks
    # whether the PMF we read off the logits is the distribution the model
    # actually samples from. Greedy must equal our argmax; sampling at T=1 must
    # reproduce our probabilities to within multinomial noise.
    print("\n[5] SAMPLING  does the model actually emit what we claim?")
    n_show, n_samp, chunk = 4, 400, 25
    agree = 0
    # a read error, as opposed to a model that will not answer: the model's own
    # samples land on the options, yet our reading puts almost no mass there
    from llm_ratings.hf_backend import normalise
    lp_shown = sc32.option_logprobs(texts32[:n_show], options)
    mass_shown = normalise(lp_shown)[1]
    misread = 0
    for i in range(n_show):
        with torch.inference_mode():
            enc = sc32.tokenizer(texts32[i], return_tensors="pt",
                                 add_special_tokens=False)
            enc = {k: v.to(sc32.device) for k, v in enc.items()}
            g = sc32.model.generate(**enc, max_new_tokens=1, do_sample=False,
                                    pad_token_id=sc32.tokenizer.pad_token_id)
            greedy = sc32.tokenizer.decode(g[0, -1])
            # num_return_sequences replicates the KV cache, so draw in chunks:
            # 400 at once needs ~10 GB on top of an fp32 7B model.
            drawn = []
            for _ in range(n_samp // chunk):
                s = sc32.model.generate(**enc, max_new_tokens=1, do_sample=True,
                                        temperature=1.0, top_k=0, top_p=1.0,
                                        num_return_sequences=chunk,
                                        pad_token_id=sc32.tokenizer.pad_token_id)
                drawn += [sc32.tokenizer.decode(t) for t in s[:, -1]]
                del s
            torch.cuda.empty_cache()
        emp = np.array([drawn.count(o) for o in options], float)
        emp_all = emp.sum()
        emp = emp / max(emp_all, 1)
        ours = f32[i]
        pred_mode = options[int(np.argmax(ours))]
        agree += int(greedy.strip() == pred_mode)
        if emp_all / n_samp >= 0.8 and mass_shown[i] < 0.5:
            misread += 1
        print("  item %d  greedy=%r our argmax=%r %s" %
              (i, greedy.strip(), pred_mode,
               "MATCH" if greedy.strip() == pred_mode else "MISMATCH"))
        print("     ours %s" % " ".join("%.3f" % x for x in ours))
        print("     emp  %s   (%d/%d draws landed on an option)"
              % (" ".join("%.3f" % x for x in emp), int(emp_all), n_samp))
        print("     max|ours-emp| %.3f   (multinomial 2sd ~ %.3f)"
              % (np.abs(ours - emp).max(),
                 2 * np.sqrt(0.25 / max(emp_all, 1))))
    print("  greedy agrees with our argmax on %d/%d items" % (agree, n_show))
    if misread * 2 >= n_show:
        print("\n!! READ ERROR: on %d/%d items the model's samples are valid "
              "options but our option_mass is < 0.5. The option token ids do "
              "not match what the model emits (see hf_backend.variant_ids)."
              % (misread, n_show))
        return 1

    print("\nSUMMARY")
    print("  padding bf16   max|dP| %.2e" % pad_err)
    print("  padding fp32   max|dP| %.2e  %s"
          % (pad32_err, "OK - padding logic is sound" if pad32_err < 1e-4
             else "SUSPECT - survives the dtype change, investigate the mask"))
    print("  positions bf16 max|dP| %.2e" % pos_err)
    print("  bf16 vs fp32   max|dP| %.2e  (ties %d -> %d)" % (prec_err, ti, ti32))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
