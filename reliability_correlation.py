# Code for split-half reliability and Spearman-Brown correction

import numpy as np
from scipy.stats import pearsonr, norm
from tqdm import tqdm

def splithalf_reliability(data, n_iterations=100):

    # calculates reliability with spearman-brown correction under n random assignments to two participant groups
    
    data = [np.array(x) for x in data if len(x) > 2]

    r = []
    for n in tqdm(range(n_iterations)):
        a, b = [], []
        for item_idx, item in enumerate(data):
            indices = np.arange(len(item))
            np.random.seed(n + item_idx)
            idx_a = np.random.choice(indices, len(indices) // 2, replace=False)
            idx_b = np.setdiff1d(indices, idx_a, assume_unique=True)
            a.append(np.mean(item[idx_a]))
            b.append(np.mean(item[idx_b]))

        r_iter, _ = pearsonr(a, b)
        r.append(r_iter)

    # Uncorrected
    mean_r = np.mean(r)
    sd_r = np.std(r, ddof=1)
    ci = norm.interval(0.95, loc=mean_r, scale=sd_r / np.sqrt(len(r)))

    # Spearman-Brown corrected: r_sb = 2r / (1 + r)
    r_sb = [2 * r_ / (1 + r_) for r_ in r]
    mean_r_sb = np.mean(r_sb)
    sd_r_sb = np.std(r_sb, ddof=1)
    ci_sb = norm.interval(0.95, loc=mean_r_sb, scale=sd_r_sb / np.sqrt(len(r_sb)))

    print(f"R (uncorrected):      mean={mean_r:.4f}, SD={sd_r:.4f}, 95% CI=[{ci[0]:.4f}, {ci[1]:.4f}]")
    print(f"R (SB-corrected):     mean={mean_r_sb:.4f}, SD={sd_r_sb:.4f}, 95% CI=[{ci_sb[0]:.4f}, {ci_sb[1]:.4f}]")

    return {
        "r": mean_r, "sd": sd_r, "ci": ci,
        "r_corrected": mean_r_sb, "sd_corrected": sd_r_sb, "ci_corrected": ci_sb
    }
