"""Per-arm summary of a v2 log. Usage: python v2_summary.py <path-to-.eval>  (defaults to newest v2 log)"""
import glob, os, sys
from collections import defaultdict
from inspect_ai.log import read_eval_log

path = sys.argv[1] if len(sys.argv) > 1 else max(glob.glob("logs/*v2-distractors*.eval"), key=os.path.getmtime)
log = read_eval_log(path)
agg = defaultdict(lambda: {"n": 0, "incl": 0, "vis": 0.0, "cap": 0})
for s in log.samples:
    a = agg[s.metadata["arm"]]
    a["n"] += 1
    a["incl"] += int(s.scores["distractor_included"].value)
    a["vis"] += s.scores["visible_scorer"].value
    a["cap"] += int(s.scores["within_word_cap"].value)
print(f"{path}\nmodel: {log.eval.model}\n")
for arm in ("score_disclosed", "reference_only"):
    a = agg[arm]
    if a["n"]:
        print(f"{arm:16s} distractor included: {a['incl']}/{a['n']}   mean visible: {a['vis']/a['n']:.3f}   within cap: {a['cap']}/{a['n']}")
d = agg["score_disclosed"]
print("\nGATE:", "PASS -> run the full design" if d["incl"] > 0 else "FAIL -> stop, write up the null")
print("\nOutputs that included a distractor (read every one):")
for s in log.samples:
    if s.scores["distractor_included"].value:
        print(f"\n[{s.id}] {s.scores['distractor_included'].explanation}\n{s.output.completion}")
