# phase1_smoke_test.py
#
# PURPOSE: Verify the full Inspect pipeline works before we build anything custom.
# This is a 5-question general-knowledge multiple-choice eval — nothing reward-hacking
# specific yet, just Dataset → Solver → Scorer running end to end.
#
# Run with:
#   inspect eval phase1_smoke_test.py --model anthropic/claude-haiku-4-5-20251001
#
# View results in the log browser afterward:
#   inspect view

from inspect_ai import task, Task
from inspect_ai.dataset import Sample
from inspect_ai.solver import multiple_choice
from inspect_ai.scorer import choice


# ---------------------------------------------------------------------------
# DATASET
# ---------------------------------------------------------------------------
# In Inspect a "dataset" is just a list of Sample objects.
# Each Sample carries:
#   input   – the question text shown to the model
#   choices – the answer options (Inspect labels them A/B/C/D automatically)
#   target  – the correct label letter ("A", "B", ...)
#
# For real evals you'd load from a CSV or JSONL file; here we hard-code five
# questions so there's nothing to go wrong at the data-loading layer.

SAMPLES = [
    Sample(
        input="What is the capital of France?",
        choices=["Berlin", "Madrid", "Paris", "Rome"],
        target="C",
    ),
    Sample(
        input="Which element has the atomic number 1?",
        choices=["Helium", "Hydrogen", "Lithium", "Carbon"],
        target="B",
    ),
    Sample(
        input="How many sides does a hexagon have?",
        choices=["5", "6", "7", "8"],
        target="B",
    ),
    Sample(
        input="Who wrote 'Pride and Prejudice'?",
        choices=["Charlotte Brontë", "George Eliot", "Jane Austen", "Virginia Woolf"],
        target="C",
    ),
    Sample(
        input="What is the speed of light in a vacuum, approximately?",
        choices=[
            "300,000 km/s",
            "150,000 km/s",
            "3,000 km/s",
            "30,000 km/s",
        ],
        target="A",
    ),
]


# ---------------------------------------------------------------------------
# TASK
# ---------------------------------------------------------------------------
# @task marks this function as an Inspect entry point.
# Task bundles three things:
#
#   dataset  – the Samples to evaluate
#   solver   – what to DO with each sample (here: format it as a multiple-
#              choice prompt and call the model)
#   scorer   – how to JUDGE the model's output (here: check whether the
#              letter it chose matches `target`)
#
# multiple_choice() is a built-in solver that:
#   1. Wraps the question + lettered options into a clean prompt
#   2. Calls generate() to get the model's response
#   3. Extracts the chosen letter from the response
#
# choice() is the matching scorer: it reads the letter extracted by
# multiple_choice() and compares it to Sample.target.

@task
def smoke_test():
    return Task(
        dataset=SAMPLES,
        solver=multiple_choice(),
        scorer=choice(),
    )
