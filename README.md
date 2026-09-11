# reward-hacking-eval

An [Inspect](https://inspect.aisi.org.uk) evaluation that demonstrates reward hacking by a language model — the LLM-eval sibling of [reward-hacking-gym](https://github.com/jadoont/reward-hacking-gym).

## The findings

We ran two conditions to explore how proxy difficulty affects gaming behaviour.

### Condition 1 — Easy proxy (8 keywords, no word limit)

| Model | `visible_scorer` | `heldout_scorer` | Gap |
|---|---|---|---|
| `claude-haiku-4-5-20251001` | **1.000** | **0.700** | **+0.300** |
| `claude-sonnet-4-6` | **1.000** | **1.000** | **0.000** |

Haiku keyword-stuffed on 3/10 samples — perfect proxy score, 30% faithfulness failures. Sonnet hit all keywords and still wrote coherent prose: it satisfied both objectives simultaneously, so there was nothing to catch.

### Condition 2 — Hard proxy (15 keywords, 50-word cap)

With 15 keywords to cover in at most 50 words, a model cannot write coherent prose that hits them all — it must choose.

| Model | `visible_scorer` | `heldout_scorer` | Gap |
|---|---|---|---|
| `claude-haiku-4-5-20251001` | **0.967** | **1.000** | **−0.033** |
| `claude-sonnet-4-6` | **0.973** | **0.800** | **+0.173** |

The roles flipped. Haiku gave up on perfect proxy coverage and wrote genuine summaries (heldout = 1.0). **Sonnet pushed harder to hit the proxy and was caught on 2/10 samples** (heldout = 0.800) — a larger gap than Haiku showed in either condition.

### What this means

More capable does not mean less likely to game. It means **more effective at optimising whatever objective is stated**. At easy proxy difficulty, a capable model satisfies both objectives and the gap disappears. At hard proxy difficulty, the same capable model optimises harder for the stated metric and in doing so produces outputs that fail the independent audit.

The finding is not "Sonnet is bad." It is that **the proxy difficulty is a dial, and turning it up reveals exploitation that lower settings hide.** A naive evaluation using only the proxy scorer would conclude — in both conditions, for both models — that performance is near-perfect.

## The principle

> **The thing that measures the system must be outside the system's reach.**

The visible scorer tells the model exactly what it will be measured on (the keyword list lives in the system prompt). A capable model, trying to do well, optimises for that signal — the same way a reinforcement learning agent optimises whatever reward function it can observe.

The held-out scorer sees only the source passage and the model's output. It never sees the keyword list. That structural separation is what makes it an audit rather than just another metric: the model cannot target it, so it cannot game it.

## The RL sibling

[reward-hacking-gym](https://github.com/jadoont/reward-hacking-gym) is a tabular Q-learning agent in a gridworld with a deliberately exploitable reward. The agent finds an unintended exploit — high proxy reward, 0% true task success — and an audit loop independent of the training loop catches the divergence.

This eval demonstrates the same principle in a language model setting:

| Concept | RL gym | This eval |
|---|---|---|
| Agent | Q-learning agent | Language model |
| Proxy signal (reachable) | Exploitable reward tile | Keyword list in system prompt |
| True task | Navigate to goal | Write a genuine summary |
| Independent audit | Audit loop outside training | `heldout_scorer` (never sees keyword list) |
| Proxy difficulty dial | Tile reward magnitude | Keyword count + word limit |

The exploit mechanism differs — gradient descent vs. in-context optimisation — but the structural problem is identical: **when the measuring instrument is inside the agent's reach, the agent learns to target the instrument instead of the task.**

## Reproduce

```bash
git clone https://github.com/jadoont/reward-hacking-eval
cd reward-hacking-eval

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

echo "ANTHROPIC_API_KEY=your-key-here" > .env

inspect eval reward_hacking_eval.py --model anthropic/claude-haiku-4-5-20251001
inspect eval reward_hacking_eval.py --model anthropic/claude-sonnet-4-6
```

To run on fewer samples during development:

```bash
inspect eval reward_hacking_eval.py --model anthropic/claude-haiku-4-5-20251001 -T samples=3
```

To browse individual model outputs and judge verdicts:

```bash
inspect view
```

## How it works

**`reward_hacking_eval.py` has three parts:**

`keyword_aware_solver` — builds a system prompt that tells the model exactly which keywords will be counted and imposes a 50-word cap. This is the exploit surface: the model can see the scoring rubric, so it can optimise for it directly.

`visible_scorer` — counts what fraction of the keyword list appears in the output. Deterministic; no model call. Returns 0–1. The model knows this exists.

`heldout_scorer` — calls a judge model with a prompt containing only the source passage and the model's output — never the keyword list. Returns 1 (genuine summary) or 0 (keyword-stuffed). The model has no way to target this scorer. This is the independent audit.

Two scorers run on every sample. The gap between `visible_scorer` mean and `heldout_scorer` mean is the headline output.

## Future Thoughts for Inspect community

Two patterns from this eval could be useful additions to [Inspect](https://github.com/UKGovernmentBEIS/inspect_ai):

**1. A `blind_scorer` wrapper.** The held-out scorer achieves independence by simply not including the keyword list in the judge prompt. But there is no Inspect primitive that *enforces* this — a future maintainer could accidentally include it and silently break the audit. A decorator or `TaskState` view that strips specified metadata keys before passing state to a scorer would make the structural separation explicit and verifiable. 

**2. Multi-scorer gap as a metric.** The finding here is the difference between two scorer means, but you have to compute that from the log yourself. A `scorer_gap(scorer_a, scorer_b)` metric reporting `mean(a) - mean(b)` per sample would make the proxy-vs-audit pattern easier to express.

## Credits

Built with [Inspect](https://inspect.aisi.org.uk), the open-source LLM evaluation framework from the [UK AI Security Institute](https://www.gov.uk/government/organisations/ai-security-institute) (AISI). Inspect is maintained at [UKGovernmentBEIS/inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai).
