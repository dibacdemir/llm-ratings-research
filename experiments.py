'''
Goals:
1. Getting the expected rating approach for some models
2. Testing whether for datasets with the full distribution of human ratings, 
   models and humans produce similar distributions of responses (besides showing similar means)


The logic for delta: two halves of the same human data differ bc of 
sampling noise, so that split-half distance is a tolerance level for 
asking whether two distributions come from the same place.

Running this code per item: 
1. Build the human counts as a vector of 7 values (how many 1s, 2s, ... 7s) 
   and the model's 7 probabilities from the expected-rating script.
2. Get delta with split_half_delta(human_counts)["delta"]
3. Call equivalence_test(llm_p, human_counts, delta=delta). 
   If similar: True, that item's model and human distributions match within sampling noise.
4. Then across a whole dataset, pass a list of pairs of llm_p, human_counts to alignment_score(items). 
   It returns three numbers: the model-human distance, a null floor from shuffling which model goes 
   with which item (chance), and a noise ceiling. The ceiling is the best a perfect model could do, 
   limited by the fact that human ratings come from a finite number of raters with noise. 
   The code draws human samples of the same size and tests how far they are from the full human 
   distribution (note: this is not exactly standard, ok for now). 
   The normalized score says where the model are between floor and ceiling 
   (1: as close as a perfect model, 0: chance). 

'''


import numpy as np

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