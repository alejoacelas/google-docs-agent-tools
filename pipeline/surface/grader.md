You are grading end-to-end runs of Google Docs tasks: an assistant got a natural request about a synthetic document, and we inspect what it did. Read-only toward Google except gdoc reads; never edit a document. Work in ~/best/tools/active/gdoc/design-review.

Inputs (filled in below): the task file, the task ids to grade, and for each configuration the run summaries folder, the copies file and copies key, the Google account, and where the BASE snapshot lives.

For each task, grade every configuration listed, one after another, so the bar is identical across configurations:

1. Read the task (prompt, checks, risk) and the run summary `RUNS/<id>.json` (tool calls with inputs and result heads, final answer, seconds). If a summary is missing, the outcome is "not-run".
2. Establish what was there before: the BASE snapshot folder (structure.json, cat.md, comments.json, info.json). Treat BASE as ground truth. If a check in the task file assumes something BASE contradicts (for example which words were bold), judge by the task's intent against BASE and say "check adjusted" in the note.
3. Inspect the document after the run: the copy id is in the copies file under the given key. Use `gdoc structure DOC`, `gdoc cat DOC --comments`, `gdoc comments DOC --all`, `gdoc info DOC`, `gdoc tabs DOC`, always with `--account ACCOUNT --json`. For comment anchors, gdoc's Python client can read documents.get with comments included (see planning/tool-matrix/pipeline/latency/fixtures.py for how it builds the Docs service; the `commentsViewMode=COMMENTS_VIEW_MODE_INCLUDED` parameter needs a raw request, as gdoc/api/docs.py does). For tasks that create a new file or folder, find it by its title (`gdoc find`), which includes the task tag `<id>-<copies key>`.
4. Judge each check: pass, fail or undecidable, with one line of concrete evidence (quoted text, style values, anchor range, reply excerpt). Reporting checks are judged from the final answer.
5. Overall outcome per task and configuration:
   - pass: every effect and reporting check passes and no preservation check fails;
   - partial: the requested effect happened, but a preservation check fails, or the answer misreports or omits something material;
   - fail: the effect did not happen, the answer is wrong, the run timed out, or the assistant refused;
   - asked: it asked a clarifying question instead of acting;
   - off-route: it reached the result through tools outside the configuration (for example the local workspace-google server or a browser) — grade the result anyway in checks, but set this outcome.
   Damage (anything changed that the user did not ask for) always goes in the note.
6. Also record the route (ordered tool names, without arguments), the number of tool calls, and seconds.

Return JSON written to the output path, a list of objects:
{"task", "config", "outcome", "checks": [{"kind", "check", "result", "evidence"}], "route": [...], "calls", "seconds", "damage", "note"}
Then reply with a compact table: task × configuration outcome, and the differences between configurations that matter.
