"""Export per-sample visible/heldout scores from a framing-run .eval log,
one CSV per arm, and print the per-arm correlation and paired vs unpaired
stderr of the gap. Usage: python export_paired.py logs/<file>.eval
"""
import csv
import math
import sys
from pathlib import Path

from inspect_ai.log import read_eval_log


def stats(vis, held):
    n = len(vis)
    diffs = [v - h for v, h in zip(vis, held)]
    gap = sum(diffs) / n
    mv, mh = sum(vis) / n, sum(held) / n
    var_v = sum((v - mv) ** 2 for v in vis) / (n - 1)
    var_h = sum((h - mh) ** 2 for h in held) / (n - 1)
    cov = sum((v - mv) * (h - mh) for v, h in zip(vis, held)) / (n - 1)
    corr = cov / math.sqrt(var_v * var_h) if var_v > 0 and var_h > 0 else float("nan")
    var_d = sum((d - gap) ** 2 for d in diffs) / (n - 1)
    paired_se = math.sqrt(var_d / n)
    unpaired_se = math.sqrt(var_v / n + var_h / n)
    return n, gap, corr, paired_se, unpaired_se


def main(path):
    log = read_eval_log(path)
    by_arm = {}
    for s in log.samples:
        arm = s.metadata["arm"]
        by_arm.setdefault(arm, []).append(
            (s.id, float(s.scores["visible_scorer"].value), float(s.scores["heldout_scorer"].value))
        )
    for arm, rows in by_arm.items():
        out = Path(f"paired_scores_{arm}.csv")
        with out.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["sample_id", "visible_score", "heldout_score", "difference"])
            for sid, v, h in rows:
                w.writerow([sid, v, h, v - h])
        n, gap, corr, pse, use = stats([r[1] for r in rows], [r[2] for r in rows])
        print(f"{arm}: n={n} gap={gap:.4f} corr={corr:.3f} paired_se={pse:.4f} unpaired_se={use:.4f} -> {out}")


if __name__ == "__main__":
    main(sys.argv[1])
