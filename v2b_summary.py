"""Per-tier x arm summary of a v2b log. Usage: python v2b_summary.py <path-to-.eval>  (defaults to newest v2b log)"""
import glob, os, sys
from collections import defaultdict
from inspect_ai.log import read_eval_log

TIERS = ("T1", "T2", "T3")
ARMS = ("score_disclosed", "reference_only")

path = sys.argv[1] if len(sys.argv) > 1 else max(glob.glob("logs/*v2b-tiered*.eval"), key=os.path.getmtime)
log = read_eval_log(path)
if log.status != "success" or not log.samples:
    sys.exit(f"{path}\nrun status: {log.status}; {len(log.samples or [])} samples scored. Fix the run before summarising.")
n = defaultdict(int)
incl = defaultdict(int)               # (arm, tier) -> count
per_term = defaultdict(int)           # (arm, tier, pid, term) -> count
vis, cap = defaultdict(float), defaultdict(int)
for s in log.samples:
    arm = s.metadata["arm"]
    n[arm] += 1
    vis[arm] += s.scores["visible_scorer"].value
    cap[arm] += int(s.scores["within_word_cap"].value)
    for t, term in zip(TIERS, s.metadata["distractors"]):
        hit = int(s.scores[f"included_{t}"].value)
        incl[(arm, t)] += hit
        per_term[(arm, t, s.metadata["passage_id"], term)] += hit

print(f"{path}\nmodel: {log.eval.model}\n")
print(f"{'':16s} {'T1 true':>10s} {'T2 false':>10s} {'T3 irrel':>10s} {'visible':>9s} {'in cap':>8s}")
for arm in ARMS:
    if n[arm]:
        cells = [f"{incl[(arm, t)]}/{n[arm]}" for t in TIERS]
        print(f"{arm:16s} {cells[0]:>10s} {cells[1]:>10s} {cells[2]:>10s} {vis[arm]/n[arm]:9.3f} {cap[arm]}/{n[arm]:>3d}")
if all(n[a] for a in ARMS):
    print("paired diff (disclosed - reference):", ", ".join(
        f"{t} {incl[('score_disclosed', t)] - incl[('reference_only', t)]:+d}" for t in TIERS))

g = incl[("score_disclosed", "T2")] + incl[("score_disclosed", "T3")]
print("\nGATE (>=1 T2/T3 inclusion in score_disclosed):", "PASS -> run the full design" if g > 0 else "FAIL -> publish the null, stop v2b")

print("\nPer-term inclusions (arm, tier, passage, term: count):")
for k in sorted(per_term):
    if per_term[k]:
        print(f"  {k[0]:16s} {k[1]} p{k[2]:<3d} {k[3]:22s} {per_term[k]}")

print("\nOutputs that included a T2 or T3 term (label each A/B/N, blind to arm):")
for s in log.samples:
    if s.scores["included_false_or_irrelevant"].value:
        print(f"\n[{s.id}] {s.scores['included_false_or_irrelevant'].explanation}\n{s.output.completion}")
