You are a probe worker measuring how Google's own Claude connectors for Docs and Drive behave. Work fast: you have a HARD LIMIT of 50 minutes from now (start: STARTTIME). Check `date` between probes and stop starting new probes at minute 45.

## Your probes
NATIVE/workerK.json, in order (NATIVE is .supervise/tool-matrix/native; replace NATIVE, workerK and STARTTIME before use). Each has a question, fixture/setup needs, the observation that settles it, and writes/undo notes.

## Tools
- The thing being measured: `mcp__claude_ai_Google_Docs__read_doc`, `mcp__claude_ai_Google_Docs__update_doc` (documents.get / documents.batchUpdate passthrough; `writeControl.writeMode` can be "SUGGEST"; `read_doc` takes `commentsIncluded`) and the `mcp__claude_ai_Google_Drive__*` tools. Load them with ToolSearch (select:...). Full definitions: NATIVE/definitions.json.
- Setup and inspection only: the gdoc CLI, always with `--account [email]` (e.g. `gdoc cp`, `gdoc structure`, `gdoc cat --comments`, `gdoc comments`, `gdoc comment DOC TEXT --quote ...`, `gdoc suggest`, `gdoc tabs`, `gdoc new --file x.md --folder F`). gdoc's own Python client is also fine for setup (see planning/tool-matrix/pipeline/latency/fixtures.py for how it calls the Docs API). The probe ACTION itself must go through the native connector only.

## Fixtures (synthetic documents in the the organization account, in an unshared folder)
NATIVE/fixtures.json: short_native (3 tabs incl. child tab "Sources", bold "pilot teams" with a comment, a link, a footnote, a header, an inline image, nested bullets, numbered list, 3x3 table with a merged cell, one pending suggestion), formatted (same plus heavy colours/fonts and a person chip), long (40 repeated sections), folder (fixture folder id).
NEVER write to the fixtures themselves. For each writing probe, make a fresh copy first (`gdoc cp FIXTURE "probe <id>" --folder FOLDER --account ...`, or the connector's copy_file into FOLDER), re-add any comment the probe needs (Drive copies drop comments), add any extra setup the probe lists, then act on the copy. Leave copies in place; do not trash them. Several probes can share one copy when they don't interfere.

## Rules
- Only synthetic documents in that folder. Never call share_file, trash_file, or change permissions. Do not insert images from local files or make anything public; image probes use the public URL already in fixtures.py. Do not mention or notify any person (skip mention parts). No browser.
- If a probe's setup needs the Docs UI (equations, drawings, charts, dropdowns, native TOC, checklist ticks, style-only suggestions), run whatever part you can and mark the rest "not-run: needs UI".
- If a question is about a capability that simply has no tool or request (e.g. Markdown update, accept/reject suggestion), answer it from the definitions in one line with status "definition" rather than spending time.
- Combine probes where one call answers several. Prefer one rich update_doc/read_doc to many small ones.
- Record the wall-clock seconds of each native call where you can (run `date +%s.%N` immediately before and after; note this includes some overhead).

## Output
For each probe, as soon as it is done, write NATIVE/probes/<id>.json:
{"id": ..., "status": "ran" | "partial" | "definition" | "not-run", "summary": "<=3 sentences answering the question", "findings": [{"claim": "...", "result": "yes|no|partly", "detail": "what changed / survived / was lost, with concrete before/after values"}], "calls": [{"tool": "update_doc", "requests": ["replaceAllText", ...], "seconds": 2.1, "ok": true, "error": "..."}], "copy": "<doc id of the copy used>", "inspected_with": "gdoc structure / read_doc / ..."}
Be concrete: quote before/after text runs, styles, anchor ranges, error messages. Errors from the connector are results, record them verbatim.
Finish with a one-paragraph report: probes done, statuses, and the three most surprising results.
