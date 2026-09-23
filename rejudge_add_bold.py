"""
rejudge_add_bold.py

Reverse test for the bold-strip rejudge. rejudge_bold.py showed that removing
** markers flips 18/18 score_disclosed FAILs to PASS. That shows bold is
NECESSARY for those failures. This script tests whether bold is SUFFICIENT:
take reference_only outputs the judge PASSED, add ** around every keyword
occurrence (mirroring the score_disclosed FAIL pattern), change nothing
else, and rejudge.

Judge prompt, parse logic and 3x majority vote are reused from rejudge_bold.py
(which reuses JUDGE_PROMPT from reward_hacking_eval.py). Not reimplemented.

Sample set: ALL reference_only heldout-PASS outputs in the Sept 21 log
(expected 100). Outputs with zero keyword matches are left out and counted.
Results reported overall and for passages 2, 4, 8 (where the score_disclosed
FAILs concentrated).

PRE-REGISTERED INTERPRETATION (fixed and committed before running):
  - Majority of bolded PASSes flip to FAIL -> bold alone is sufficient to
    cause a FAIL. Combined with the strip test, the judge's verdict is driven
    by formatting in both directions; the Sept framing gap is predominantly
    a judge-formatting artifact.
  - Few flip (<= 10% overall) -> bold is necessary but not sufficient. The
    score_disclosed FAILs combine bold with something else (e.g. keyword-dense,
    choppy prose). The framing effect then has a content component that the
    strip test could not see.
  - In between -> report the rate as-is, with the passage breakdown; no
    headline claim either way.

Run: python rejudge_add_bold.py
"""

import argparse
import ast
import asyncio
import json
import re
from collections import defaultdict
from pathlib import Path

from inspect_ai.log import read_eval_log
from inspect_ai.model import get_model

from rejudge_bold import rejudge_majority

FOCUS_PASSAGES = {"2", "4", "8"}


def add_bold(text: str, keywords: list[str]) -> tuple[str, int]:
    """Wrap each whole-word, case-insensitive keyword occurrence in **.
    Longer keywords first so 'carbon dioxide' wins over 'carbon'.
    Returns (new_text, number_of_spans_bolded)."""
    kws = sorted({k.strip() for k in keywords if k.strip()}, key=len, reverse=True)
    pattern = re.compile(
        r"(?<![\w*])(" + "|".join(re.escape(k) for k in kws) + r")(?![\w*])",
        re.IGNORECASE,
    )
    new_text, n = pattern.subn(lambda m: f"**{m.group(1)}**", text)
    return new_text, n


def load_passes(log_path: str):
    log = read_eval_log(log_path)
    passes = []
    for s in log.samples:
        if s.metadata.get("arm") != "reference_only":
            continue
        held = s.scores.get("heldout_scorer")
        if held is None:
            raise KeyError(f"{s.id}: no heldout_scorer; got {list(s.scores)}")
        if held.value != 1.0:
            continue
        kws = s.metadata["keywords"]
        if isinstance(kws, str):
            kws = ast.literal_eval(kws)
        passes.append((s.id, str(s.metadata.get("passage_id")),
                       s.metadata["source"], s.output.completion, kws))
    return passes


async def run(log_path: str, out_path: str, judge_model: str):
    passes = load_passes(log_path)
    judge = get_model(judge_model)
    print(f"{len(passes)} reference_only PASS outputs found")

    results, skipped = [], []
    for sid, pid, source, text, kws in passes:
        bolded, n_spans = add_bold(text, kws)
        if n_spans == 0:
            skipped.append(sid)
            continue
        majority, votes, expl = await rejudge_majority(judge, source, bolded, n=3)
        results.append({
            "sample_id": sid, "passage_id": pid, "original_verdict": "PASS",
            "bold_spans_added": n_spans, "rejudge_majority": majority,
            "rejudge_votes": votes, "flipped": majority == "FAIL",
            "bolded_text": bolded, "explanations": expl,
        })
        print(f"  {sid} (+{n_spans} bold): PASS -> {majority} {votes}")

    by_passage = defaultdict(lambda: [0, 0])
    for r in results:
        by_passage[r["passage_id"]][0] += r["flipped"]
        by_passage[r["passage_id"]][1] += 1

    n, f = len(results), sum(r["flipped"] for r in results)
    fn = sum(v[1] for p, v in by_passage.items() if p in FOCUS_PASSAGES)
    ff = sum(v[0] for p, v in by_passage.items() if p in FOCUS_PASSAGES)
    split = sum(len(set(r["rejudge_votes"])) > 1 for r in results)

    print("\n=== Add-bold rejudge ===")
    print(f"Overall flipped PASS -> FAIL: {f}/{n}")
    print(f"Passages 2/4/8:               {ff}/{fn}")
    for p in sorted(by_passage, key=lambda x: int(x) if x.isdigit() else x):
        print(f"  passage {p}: {by_passage[p][0]}/{by_passage[p][1]}")
    print(f"Split votes (not unanimous):  {split}/{n}")
    print(f"Skipped (no keyword matches): {len(skipped)} {skipped}")

    Path(out_path).write_text(json.dumps({
        "summary": {"flipped": f, "n": n, "focus_flipped": ff, "focus_n": fn,
                    "split_votes": split, "skipped": skipped,
                    "by_passage": {p: {"flipped": v[0], "n": v[1]} for p, v in by_passage.items()}},
        "results": results}, indent=2))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="logs/2026-09-21T17-56-41-00-00_tonight-audit_R8cBcE49GCaHpWwrWtrxFR.eval")
    ap.add_argument("--out", default="rejudge_add_bold_results.json")
    ap.add_argument("--judge-model", default="anthropic/claude-haiku-4-5-20251001")
    a = ap.parse_args()
    asyncio.run(run(a.log, a.out, a.judge_model))
