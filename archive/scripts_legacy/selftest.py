#!/usr/bin/env python
"""Check the plumbing without a GPU or a model download.

Loads a real task, builds real prompts, then substitutes a *synthetic* model
whose PMF is a noised version of the human distribution, and runs the full
distribution pipeline on it. Also runs three sanity checks on the stats:

  identical distributions        -> W1 == 0, similar == True
  a deliberately shifted model   -> similar == False
  a model that IS the human PMF  -> normalized alignment near 1

    python scripts/selftest.py [--task amouyal2024_plausibility] [--n 60]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402

from llm_ratings import data, dist, prompt as prompt_mod  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="amouyal2024_plausibility")
    ap.add_argument("--n", type=int, default=60)
    args = ap.parse_args(argv)

    print("[1] locate + load task")
    loc = data.find_task(args.task)
    instr = prompt_mod.read_instructions(loc["instructions"])
    items = data.load_items(loc["csv"], limit=args.n, require_individual=True)
    lo, hi = data.resolve_scale(instr, items)
    k = hi - lo + 1
    print("    %s (%s): %d items, scale %d-%d, placeholder %s"
          % (loc["task"], loc["source"], len(items), lo, hi,
             prompt_mod.placeholders(instr)))
    assert items and k >= 2

    print("[2] prompt construction")
    p0 = prompt_mod.build_prompt(instr, items[0]["unit"], lo, hi, suffix="auto")
    assert "<<{" not in p0 and items[0]["unit"][:20] in p0
    print("    ...%s" % p0[-160:].replace("\n", " / "))

    print("[3] human counts")
    counts = [data.human_counts(it["individual"], lo, hi)[0] for it in items]
    assert all(sum(c) == len(it["individual"])
               for c, it in zip(counts, items)), "ratings fell outside the scale"
    print("    median raters/item: %d" % np.median([sum(c) for c in counts]))

    print("[4] stats sanity")
    c0 = counts[0]
    hp = np.asarray(c0, float) / sum(c0)
    same = dist.per_item(hp, c0, n_splits=400, n_boot=400)
    assert abs(same["W1"]) < 1e-12, same
    assert same["similar"] is True, same
    shifted = np.zeros(k); shifted[0] = 1.0
    if np.argmax(hp) != 0:
        bad = dist.per_item(shifted, c0, n_splits=400, n_boot=400)
        assert bad["W1"] > same["W1"], bad
        print("    same dist W1=%.4f similar=%s | shifted W1=%.4f similar=%s"
              % (same["W1"], same["similar"], bad["W1"], bad["similar"]))

    print("[5] alignment: perfect model vs noisy model vs shuffled")
    hps = [np.asarray(c, float) / sum(c) for c in counts]
    perfect = dist.alignment_score(list(zip(hps, counts)), n_boot=200)
    rng = np.random.default_rng(0)
    noisy = [0.6 * p + 0.4 * rng.dirichlet(np.ones(k)) for p in hps]
    noisy_res = dist.alignment_score(list(zip(noisy, counts)), n_boot=200)
    print("    perfect: %s" % perfect)
    print("    noisy  : %s" % noisy_res)
    assert perfect["normalized"] > noisy_res["normalized"]
    assert perfect["normalized"] > 0.8

    print("[6] W1 decomposition agrees with Ted's W1 and is additive")
    from analyze_run import w1_decompose

    rng2 = np.random.default_rng(1)
    A = rng2.dirichlet(np.ones(k), size=200)
    B = rng2.dirichlet(np.ones(k), size=200)
    w1, loc, shape = w1_decompose(A, B)
    ted = np.array([dist.wasserstein1_pmf(A[i], B[i]) for i in range(len(A))])
    assert np.abs(w1 - ted).max() < 1e-12, np.abs(w1 - ted).max()
    v = np.arange(k)
    assert np.abs(loc - np.abs(A @ v - B @ v)).max() < 1e-12
    assert np.abs((loc + shape) - w1).max() < 1e-12       # additive
    assert (shape >= -1e-12).all()                        # W1 >= |mean diff|
    # a pure shift of a point mass is all location, no shape
    p = np.zeros(k); p[0] = 1.0
    q = np.zeros(k); q[-1] = 1.0
    w, l, s = w1_decompose(p[None], q[None])
    assert abs(float(s)) < 1e-12 and abs(float(l) - (k - 1)) < 1e-12, (w, l, s)
    # two distributions with the same mean are all shape, no location:
    # mass split on the two ends vs mass concentrated at the midpoint
    p2 = np.zeros(k); p2[0] = p2[-1] = 0.5
    q2 = np.zeros(k)
    if k % 2:
        q2[(k - 1) // 2] = 1.0
    else:
        q2[k // 2 - 1] = q2[k // 2] = 0.5
    for name, d in (("p2", p2), ("q2", q2)):
        assert abs(d.sum() - 1) < 1e-12, "%s is not a PMF (sums to %.3f)" % (name,
                                                                            d.sum())
    w, l, s = w1_decompose(p2[None], q2[None])
    assert abs(float(l)) < 1e-12 and float(s) > 0, (w, l, s)
    print("    ok (max |W1 - Ted's W1| = %.2e over 200 random pairs)"
          % np.abs(w1 - ted).max())

    print("[7] logprob -> PMF math (no model)")
    try:
        from llm_ratings.hf_backend import expected_rating, normalise
    except ImportError as exc:
        print("    skipped (torch/transformers not importable here: %s)" % exc)
    else:
        lp = np.log([[0.1, 0.2, 0.3, 0.05, 0.05, 0.1, 0.1]])
        pmf, mass = normalise(lp)
        assert abs(pmf.sum() - 1) < 1e-12 and abs(mass[0] - 0.9) < 1e-9
        assert abs(expected_rating(pmf[0], list(range(1, 8)))
                   - float(np.dot(pmf[0], np.arange(1, 8)))) < 1e-12
        print("    ok (option_mass=%.3f)" % mass[0])

    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
