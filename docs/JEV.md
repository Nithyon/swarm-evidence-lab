# Optional Jev review helper

This adapter belongs to Swarm Evidence Lab. It has no code import, credentials, runtime dependency, or shared settings with the interruptible agents project.

Jev can help classify selected text. The product uses three narrow questions: whether a shared plan is visible, whether observed actions support it, and whether a peer warning or refusal is visible.
Every question includes an uncertain or insufficient-evidence choice.
These suggestions do not establish different operators, model identity, permission, causation, or harmful collusion.

The adapter follows the [official HTTP API](https://docs.typesafe.ai/api).
It pins `jev-1.13.0` by default and records the returned model version, prompt version, source IDs, excerpt hashes, usage, and elapsed time.
No accuracy or latency claim is made for this project.
Provider-reported confidence remains separate from human evidence judgments.

## Enable this project only

Use `SWARM_JEV_API_KEY`, `SWARM_JEV_ENABLED`, and optionally `SWARM_JEV_MODEL`.
The adapter deliberately does not use another project's `TYPESAFE_API_KEY` or load its environment files.
Set the key through your local secret manager or process environment. Never commit it or paste it into a review.

After setting the key, start a new server process:

```powershell
$env:SWARM_JEV_ENABLED = '1'
$env:SWARM_JEV_MODEL = 'jev-1.13.0'
python app.py --port 8878
```

The default server may already occupy port 8877. Open the port you started.
Without both the flag and key, Jev stays off and manual review works.

## Use the helper

Select records in Trace evidence. Open Jev review helper.
Preview the exact excerpts, then allow that one request to send them to TypeSafe.
The app does not send a full dataset automatically.
The request includes at most 12 records, 6,000 characters per text field, and 28 KB of serialized content.
Truncated excerpts are marked. Earlier or later context may be missing.
Check source terms before processing records through any external provider.

The connection uses the official fixed HTTPS endpoint, a three-second timeout, and no automatic retries.
Unavailable or invalid responses return to manual review, without invented probabilities.
Recent triage results and JSON exports remain local.
Jev cannot modify evidence reviews or take actions against agents.

## Validate before relying on it

The local tests use an injected test transport. They check disabled behavior, permission, limits, malformed responses, timeouts, and project separation.
They do not establish a working live account or detector quality.
No live paid request was made during this build.

Before treating suggestions as a detector, collect independent human labels and compare missed cases and false alarms on held-out records.
Include ordinary cooperation, preserved wiki text, common incentives, disagreement, and reports without corrective action.
