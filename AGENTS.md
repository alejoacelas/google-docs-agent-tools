# Google Docs agent tools

Public findings on where Claude's Google Docs connector falls short (October 2026), with the data and harness to replicate them, plus an earlier comparison of gog, Claude native and Codex native. `README.md` presents the findings and how to replicate them; `CONNECTOR-GAPS.md` is the full report; `connector-gaps/` holds its data, harness and `REPLICATING.md`. `METHODOLOGY.md`, `docs/` (the GitHub Pages review site), `data/` and `pipeline/` belong to the earlier comparison.

The working pipeline, raw transcripts and document snapshots live in the private gdoc design-review repository. `CONNECTOR-GAPS.md` is a verbatim copy of `planning/connector-gaps/REPORT.md` there. Regenerate everything else with `python3 planning/tool-matrix/pipeline/publish.py <path to this repo>`, which scrubs IDs, accounts and emails; never copy raw run files here. Keep numbers in README, METHODOLOGY and CONNECTOR-GAPS in step with `docs/*.json` and `connector-gaps/data/runs.json`.
