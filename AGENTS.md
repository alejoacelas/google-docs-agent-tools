# Google Docs agent tools

Public results of a comparison of gog, Claude native and Codex native on everyday Google Docs tasks (October 2026). `README.md` gives the results, `METHODOLOGY.md` the method and how each number maps to a file; `docs/` is the GitHub Pages review site.

The working pipeline, raw transcripts and document snapshots live in the private gdoc design-review repository (`planning/tool-matrix/`, `.supervise/tool-matrix/`). Regenerate this repository from there with `python3 planning/tool-matrix/pipeline/publish.py <path to this repo>`, which scrubs IDs, accounts and emails; never copy raw run files here. Keep numbers in README and METHODOLOGY in step with `docs/*.json`.
