"""Distributional comparison of model vs human ratings.

The four functions below (`wasserstein1_pmf`, `equivalence_test`,
`split_half_delta`, `alignment_score`) are Ted's, kept verbatim so results stay
comparable; everything after the marker is thin plumbing around them.

Logic, in one line: two halves of the *same* human data already differ because
of sampling noise, so the split-half W1 is the natural tolerance for asking
whether the model's distribution comes from the same place.
"""

import numpy as np

# --------------------------------------------------------------------------
# Ted's code — do not edit without telling him
# --------------------------------------------------------------------------


def wasserstein1_pmf(p, q):
    # p, q: length-7 PMFs on points 1..7
    # W1 = L1 distance between CDFs at the 6 interior cut points
    cp = np.cumsum(p)[:-1]
    cq = np.cumsum(q)[:-1]
    return np.sum(np.abs(cp - cq))


def equivalence_test(llm_p, human_counts, delta, n_boot=10000, alpha=0.05, seed=0):
    rng = np.random.default_rng(seed)
    llm_p = np.asarray(llm_p, float); llm_p /= llm_p.sum()
    counts = np.asarray(human_counts, float)
    N = int(counts.sum())
    human_p = counts / N
    point = wasserstein1_pmf(llm_p, human_p)
    boot = np.array([
        wasserstein1_pmf(llm_p, rng.multinomial(N, human_p) / N)
        for _ in range(n_boot)
    ])
    upper = np.quantile(boot, 1 - alpha)   # one-sided 95% upper bound
    return {"W1": point, "upper_95": upper, "delta": delta,
            "similar": bool(upper < delta)}


def split_half_delta(human_counts, n_splits=10000, quantile=0.5, seed=0):
    rng = np.random.default_rng(seed)
    counts = np.asarray(human_counts, int)
    K = len(counts)
    raw = np.repeat(np.arange(K), counts)      # expand counts to raw responses
    N = len(raw)
    h = N // 2
    dists = np.empty(n_splits)
    for i in range(n_splits):
        rng.shuffle(raw)
        a = np.bincount(raw[:h], minlength=K); a = a / a.sum()
        b = np.bincount(raw[h:], minlength=K); b = b / b.sum()
        dists[i] = wasserstein1_pmf(a, b)
    return {"delta": float(np.quantile(dists, quantile)),  # median split-half W1
            "mean": float(dists.mean()),
            "dist": dists}


def alignment_score(items, n_boot=2000, seed=0):
    # items: list of (llm_p, human_counts). Uses ALL raters; model stays clean.
    rng = np.random.default_rng(seed)
    llm   = [np.asarray(p, float)/np.sum(p) for p, _ in items]
    hum_c = [np.asarray(c, int) for _, c in items]
    hum_p = [c/c.sum() for c in hum_c]
    Ns    = [int(c.sum()) for c in hum_c]
    n = len(items)

    # model vs full-N human dist, averaged over items
    model = np.mean([wasserstein1_pmf(llm[i], hum_p[i]) for i in range(n)])

    # ceiling: where a perfect clean model would sit = one-sided N-rater noise.
    # bootstrap a fresh N-rater sample per item and measure W1 back to the full dist.
    ceil = np.mean([
        np.mean([wasserstein1_pmf(hum_p[i], rng.multinomial(Ns[i], hum_p[i])/Ns[i])
                 for i in range(n)])
        for _ in range(n_boot)
    ])

    # null (floor): shuffle which model dist pairs with which item
    null = np.mean([
        np.mean([wasserstein1_pmf(llm[p[i]], hum_p[i]) for i in range(n)])
        for p in (rng.permutation(n) for _ in range(n_boot))
    ])

    norm = (null - model) / (null - ceil)   # 1 = at human ceiling, 0 = chance
    return {"model": round(model,3), "null": round(null,3),
            "ceiling": round(ceil,3), "normalized": round(norm,3)}


# --------------------------------------------------------------------------
# plumbing
# --------------------------------------------------------------------------


def per_item(llm_p, counts, n_splits=2000, n_boot=2000, alpha=0.05, seed=0,
             quantile=0.5):
    """delta from the item's own split-half noise, then the equivalence test."""
    n = int(np.sum(counts))
    if n < 4:
        return {"n": n, "W1": float("nan"), "upper_95": float("nan"),
                "delta": float("nan"), "similar": None,
                "note": "too few raters to split"}
    d = split_half_delta(counts, n_splits=n_splits, quantile=quantile, seed=seed)
    res = equivalence_test(llm_p, counts, delta=d["delta"], n_boot=n_boot,
                           alpha=alpha, seed=seed)
    res["n"] = n
    res["delta_mean"] = d["mean"]
    return res


def pearson(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 3 or x.std() == 0 or y.std() == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def _rank(a):
    a = np.asarray(a, float)
    order = a.argsort(kind="mergesort")
    ranks = np.empty(len(a), float)
    ranks[order] = np.arange(len(a), dtype=float)
    # average ties
    sa = a[order]
    i = 0
    while i < len(sa):
        j = i
        while j + 1 < len(sa) and sa[j + 1] == sa[i]:
            j += 1
        if j > i:
            ranks[order[i : j + 1]] = (i + j) / 2.0
        i = j + 1
    return ranks


def spearman(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 3:
        return float("nan")
    return pearson(_rank(x[ok]), _rank(y[ok]))
