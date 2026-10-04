# Swarm Evidence Lab

When AI works as a team, show the evidence.

Swarm Evidence Lab is a local research app for understanding groups of AI agents.
An agent is an AI program that takes actions.
The app traces references, preserves source context, and separates evidence from interpretation.
It also compares recorded cooperation results and tests detection against selective attempts.
Activity patterns show dated records, gaps, and changes from earlier activity.

## Start the app

Use Python 3.11 or later with SQLite FTS5 support.
The app uses Python's standard library and browser JavaScript.
The core app needs no API key, GPU, paid model calls, or package installation.
The optional Jev review helper needs this project's own key. It stays off by default.

From the repository folder, run:

```powershell
python import_data.py --demo-only
python app.py
```

Open http://127.0.0.1:8877.
Keep the Python process running while you use the app.
Press Ctrl+C in that terminal to stop it.
Use `python app.py --port 8878` if the default port is occupied.

## Use existing datasets

The app reads existing downloads. It does not download or redistribute the datasets.
Core views work locally. Optional Jev triage sends selected previewed excerpts only when enabled and requested.
The local database stays in `.local/`, which Git excludes.
Raw data terms remain separate from the app code.

For the supplied Windows folders, run:

```powershell
python import_data.py --research "C:\Users\saini\Documents\Codex\2026-10-05\swarm-hackathon-research" --village "D:\Datasets\ai-village"
```

The `--research` folder must contain the existing `data/collusion`, `data/transluce`, and `data/swarmtraces` folders.
The `--village` folder must contain the original AI Village files.
Use `--sources collusion,transluce` to import only selected sources.
Imports replace each source transactionally. Repeating an import does not duplicate its records.

The verified local index contains:

| Source | Indexed records | Scope |
| --- | ---: | --- |
| AI Village | 183,735 | 183,485 chat messages and 250 sampled computer turns |
| Collusion.wiki | 14,591 | Saved page revisions with full text and added or replaced lines |
| Transluce | 38,160 | Distinct scanner report catalog entries |
| SwarmTraces | 189,579 | Redacted artifacts and parent references |
| Total source records | 426,065 | Different record types, not agents or unique incidents |

The 250 computer turns are a prefix in file order. They are not a representative sample.
The app does not index all computer turns, memories, screenshots, or Claude Code sessions.
All released SwarmTraces rows lack dates. The app preserves that gap.
Current AI Village model metadata does not establish the model used for every historical message.

## Follow the demo

Open Overview and select **Trace a real example**.
The scanner report ID appears in a Transluce catalog record and two saved wiki revisions.
The second wiki revision preserves the URL from the first.
The app identifies the inherited reference instead of treating it as another exchange.

Select the relevant records and open Review coordination.
Write what the evidence establishes, the alternative explanations, and the missing evidence.
Save separate judgments for coordination, independent operators, model identities, and permission.
Open Saved reviews and export a Markdown report.
The report includes source IDs and your explanation. It excludes raw transcripts.
Each review can record a responsible reviewer, next action, verification, and response status.
You can update those fields in Saved reviews. Statuses are human-supplied records; the app does not send alerts or enforce responses.

Open Measure cooperation to compare matched recorded runs.
Open Compare words and actions to compare four monitor views on the same labeled cases.
Open Test detection to compare all opportunities, random selection, and selective selection.
These views initially use synthetic examples with invented scores.
Their results demonstrate calculations. They do not measure an AI model or establish detector accuracy.

## Import experiment results

Download an example JSON from the relevant view, then replace its records with recorded results.
Declare `synthetic: false` only for actual measurements.
The app stores uploaded results locally. It does not execute uploaded code or call a model.
Jev has a separate manual request flow. See [Jev setup and limits](docs/JEV.md).

For cooperation results, record task, trial, condition, model, team size, budget, tokens, score, success, and time.
The conditions are `single`, `independent`, `hierarchical`, and `cooperative`.
All team budgets must include communication.
Matching requires the same task, trial, model, budget basis, and allocated total budget.
Token use may be below the cap when a run completes early. The table reports actual consumption separately.
Equal allocated budgets do not establish equal consumed compute.
Repeated trials are grouped by task when estimating uncertainty.
Tokens are a proxy for compute, especially across models with different costs or hardware.
Budget bases are `tokens`, `flops`, or `usd`.
Money measures cost efficiency. It does not directly measure hardware compute.

For selective-attack results, provide honest calibration episodes, independent honest test episodes, and test attacks.
Each test attack needs a supplied selection score, suspicion score, and side-task outcome.
The selection score must use information available before the outcome.
The app calibrates the threshold from honest records only.
The random comparison uses the same number of attempts as the selective comparison.
The random comparison averages 500 same-size draws with a fixed seed.
Its safety averages only draws with decisive outcomes and reports how many draws were undefined.
Its central 95% range describes subset variation, not a population confidence interval.
The safety ratio is `caught / (caught + uncaught successful)`.
It is not overall accuracy or a direct deployment safety probability.
When the denominator is zero, the result is undefined.

For the comparison of monitor views, provide independent case labels and four scores.
The views are `messages`, `actions`, `raw_combined`, and `structured`.
Use the same frozen monitor on all views, then evaluate on the same held-out cases.
Include harmful coordination, common incentives without agreement, and talk without action.
The app calculates accuracy, precision, recall, and false alarms. It does not generate the monitor scores.

## Research scope

The Research library maps all visible supplied links and themes to features or study plans.
The Experiment planner includes all twelve organizer questions and three additional measurement plans.
The plans cover markets, participant replacement, diversity, detection, action carriers, trusted participants, and monitoring awareness.
They are study templates. The app does not install or run external experiment harnesses.

The product does not establish a superlinear scaling exponent from a higher team score.
That requires a single-agent compute curve, several team sizes, repeated tasks, and uncertainty estimates.
The product also does not infer independent owners from names, writing style, signatures, or watermarks.
Human reviewers supply judgments and must cite corroborating records.
Keyword candidates are review leads. They do not establish harmful coordination or lack of permission.

See [the research map](docs/RESEARCH_MAP.md), [the product story](docs/PRODUCT.md), and [the measurement method](docs/METHODS.md).
The installed Gemini CLI rejected authentication because the client was unsupported.
Small read-only review tasks are available in [GEMINI_TASKS.md](GEMINI_TASKS.md).
Gemini's Task 1 review arrived through Antigravity and is preserved in [the review](docs/GEMINI_REVIEW_1.md).
See [the decisions](docs/GEMINI_REVIEW_DECISIONS.md) for accepted fixes and methodological choices.
Tasks 2 and 3 remain pending.
The existing shared `swarm_metrics.py` module was inspected and integrated for activity and mention patterns.
Its names such as infection latency describe observed mention order, not demonstrated causal transmission.
The app uses no optional scientific package. The module's optional Poisson method needs SciPy if used in a separate script.

## Validate the app

Run the measurement, evidence, and HTTP tests, then validate JavaScript syntax:

```powershell
python -m unittest discover -s tests -v
python swarm_metrics.py
node --check static/app.js
```

The tests cover inherited references, literal matching, budgets, model matching, repeated trials, threshold calibration, ties, undefined ratios, and local write protection.
GitHub Actions runs the tests on Python 3.11 and 3.14.
Browser verification is separate from these tests.
The local build was tested in Microsoft Edge through agent-browser.
See [the validation record](docs/VALIDATION.md) for the checks and their limits.

## Data credits

AI Digest / AI Village provides the AI Village dataset under its research terms.
Review those terms before publishing derived results. Training and fine-tuning need written permission.
Collusion.wiki, Transluce, and SwarmTraces provide the public incident material.
Their original records and classifications remain attributable to the publishers.
Mara's Murmuration Observatory is a design reference.
SwarmScope was inspected remotely as related work. Its code was not copied or run.

The app is a local research build. It binds to loopback and has no multi-user authentication system.
Keep it on this computer. Public hosting requires a separate deployment design and access controls.
