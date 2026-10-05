You are grading how well {name} supports everyday Google Docs tasks. Its code is closed, so grade from three sources, in this order of authority:
1. The live probe log: {probes}. Each probe ran a real call on a synthetic document and records what changed and what survived. A probe result overrides anything the definitions or Google's documentation suggest.
2. The connector's tool definitions, copied verbatim: {definitions}. {passthrough}
3. Google's public reference for those requests (https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/request), from your own knowledge. Do not fetch anything.
- Taxonomy of items, properties and promises: {acceptance} (§2 lists what must survive for each item).
{extra}
Do not call any tool that contacts Google. Read the files above.

For each task, find the BEST route a competent agent could take with this tool alone, starting from a known document ID and a target described in document terms. Then grade:

coverage — exactly one of:
- native: the route achieves the outcome, scoped to the requested target, and the Google requests overwrite or drop nothing that ACCEPTANCE §2 says must survive for the items involved. For reads: the output actually contains the requested content/properties with their relationships.
- lossy: the route achieves the core outcome, but changes or drops something that must survive. Name the loss in the note and cite the probe or the request's documented behaviour.
- cannot-target: a route makes the change but cannot confine it to the requested target (replace-all only, silently first match with no way to choose).
- no-route: nothing in the tool achieves the outcome, including by composing calls. A tool that safely refuses but cannot complete the task is no-route; say "refuses safely" in the note.
For tasks tagged concurrent or lost-response, the condition is part of the outcome: silently overwriting the collaborator's change or duplicating work is lossy. `writeControl.requiredRevisionId` is the documented guard.

route — the ordered tool calls on that best route, by tool name without prefix ({route_examples}); empty for no-route. Include the read needed to find indices. Mark optional=true for calls needed only sometimes. Exclude verification reads unless the route cannot proceed without them.

flags — caller-mechanics when the caller must compute indices or write raw request bodies (set it whenever the route uses {raw_tool}); depends-on-google when no probe settles the grade and Google's documentation leaves it open (state your best reading in the note).

evidence — 1–3 entries. Cite a probe as `probe:<id>` and the definition as `definition:<tool name>`. A no-route grade cites the definition list that lacks the capability.

In the note, say "probe-backed" when a probe decides the grade, otherwise "predicted". Be specific and terse. Grade every task you are given, in order, with the exact task id.
