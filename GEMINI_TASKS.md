# Gemini tasks

Codex owns app.py, lab.py, import_data.py, static/, fixtures/, and tests/.
Gemini reviews one small task at a time. Read files and return findings in your response.
Do not edit files, install packages, run recorded dataset code, change Git, or publish anything.
Do not inspect secrets, credentials, unrelated workspaces, or raw research datasets.

## Task 1: Review the measurements

Read lab.py. Review cooperation(), selectivity(), and their validation functions.
Identify at most five concrete bugs or misleading interpretations.
For each finding, provide the function, a small example, and a proposed correction.
Prioritize equal budgets, independent test data, tied suspicion scores, empty denominators, and repeat trials.
Distinguish a bug from an optional research extension. Do not propose a replacement application.

## Task 2: Review evidence claims

Read docs/RESEARCH_MAP.md, lab.py, and import_data.py after Codex finishes them.
Identify unsupported claims about identity, model history, authorization, causation, or information spread.
Return at most five precise findings. Do not add confidence percentages without measured evidence.

## Task 3: Review the user flow

Read static/index.html, static/app.js, and README.md after Codex finishes them.
Describe the shortest path to trace evidence, save a review, compare cooperation, and run an audit stress test.
Identify confusing labels, inaccessible controls, or missing explanations. Return at most five fixes.

## Current handoff

Task 1 is received and addressed. Read docs/GEMINI_REVIEW_DECISIONS.md for the decisions.
Proceed with Task 2 on the current code. Save findings in .local-gemini-task-2.txt in this repository.
Pay particular attention to the new activity and mention-pattern calculations in lab.py and swarm_metrics.py.
Distinguish recorded-label order from communication or causal transmission.
Save Task 3 separately in .local-gemini-task-3.txt after the Task 2 review.
Codex continues to own source edits and publication.
