"""Error bars for agent evals, standard library only. Equation numbers are from Miller (2024),
"Adding Error Bars to Evals"; pass@k is from Chen et al. (2021) and pass^k from Yao et al. (2024).

A score is a number per run (1 right, 0 wrong). Runs of one task are not independent, so every
function here first averages them into one score per task.
"""
from math import comb, sqrt
from statistics import NormalDist, fmean


def z(p):
    """The (1 - p) quantile of the standard normal: z(0.025) = 1.96."""
    return NormalDist().inv_cdf(1 - p)


def per_task(runs):
    """{task: [score, score, ...]} -> {task: mean score}."""
    return {t: fmean(s) for t, s in runs.items()}


def se(x):
    """Standard error of the mean of independent values (Eq. 1)."""
    m = fmean(x)
    return sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1) / len(x))


def se_clustered(x, clusters):
    """Standard error when the values come in related groups (Eq. 4). clusters[i] names x[i]'s group."""
    m, n = fmean(x), len(x)
    cross = sum((x[i] - m) * (x[j] - m) for i in range(n) for j in range(n)
                if i != j and clusters[i] == clusters[j])
    return sqrt(se(x) ** 2 + cross / n ** 2)


def se_paired_clustered(d, clusters):
    """Clustered standard error of a mean difference, from the per-task differences (Eq. 8)."""
    m, n = fmean(d), len(d)
    return sqrt(sum((d[i] - m) * (d[j] - m) for i in range(n) for j in range(n)
                    if clusters[i] == clusters[j])) / n


def ci(mean, stderr, level=0.95):
    """Normal-approximation confidence interval (Eq. 3)."""
    h = z((1 - level) / 2) * stderr
    return mean - h, mean + h


def compare(a, b, clusters=None):
    """Paired comparison of two conditions on the same tasks (Section 4.2).

    a, b: {task: [scores]}. Returns the mean difference a - b, its paired standard error, the
    unpaired one for contrast, the 95% interval and the correlation of the per-task means."""
    tasks = sorted(a)
    xa, xb = [fmean(a[t]) for t in tasks], [fmean(b[t]) for t in tasks]
    d = [p - q for p, q in zip(xa, xb)]
    paired = se(d) if clusters is None else se_paired_clustered(d, [clusters[t] for t in tasks])
    ma, mb = fmean(xa), fmean(xb)
    cov = sum((p - ma) * (q - mb) for p, q in zip(xa, xb))
    var = sqrt(sum((p - ma) ** 2 for p in xa) * sum((q - mb) ** 2 for q in xb))
    return {"diff": fmean(d), "se": paired, "se_unpaired": sqrt(se(xa) ** 2 + se(xb) ** 2),
            "ci": ci(fmean(d), paired), "corr": cov / var if var else float("nan"), "n": len(tasks)}


def variance_parts(runs):
    """Split the variance of single-run scores into the part between tasks, Var(x), and the
    average part within a task, E[sigma_i^2] (Section 3). Needs at least two runs per task."""
    xs = [fmean(s) for s in runs.values()]
    within = fmean([sum((v - fmean(s)) ** 2 for v in s) / (len(s) - 1) for s in runs.values()])
    k = fmean([len(s) for s in runs.values()])
    between = max(0.0, sum((x - fmean(xs)) ** 2 for x in xs) / (len(xs) - 1) - within / k)
    return between, within


def mde(n, omega2, var_a=0.0, var_b=0.0, k_a=1, k_b=1, alpha=0.05, power=0.8):
    """Minimum detectable effect for n tasks in a paired comparison (Eq. 10)."""
    return (z(alpha / 2) + z(1 - power)) * sqrt((omega2 + var_a / k_a + var_b / k_b) / n)


def tasks_needed(delta, omega2, var_a=0.0, var_b=0.0, k_a=1, k_b=1, alpha=0.05, power=0.8):
    """Number of independent tasks needed to detect a difference delta (Eq. 9)."""
    return (z(alpha / 2) + z(1 - power)) ** 2 * (omega2 + var_a / k_a + var_b / k_b) / delta ** 2


def pass_at_k(n, c, k):
    """Chance that at least one of k runs drawn from n (c of them right) is right (Chen et al.)."""
    return 1.0 if n - c < k else 1 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n, c, k):
    """Chance that all k runs drawn from n (c of them right) are right (Yao et al.)."""
    return comb(c, k) / comb(n, k)
