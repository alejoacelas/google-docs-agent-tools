You are grading how well {name} supports everyday Google Docs tasks, from its source code only.
- Source checkout at the version being graded ({version}, commit {sha}): {dir}
- Citation permalink base: {url}  (cite as {url}<path>#L10-L20)
- {inventory}
- Taxonomy of items, properties and promises: {acceptance} (§2 lists what must survive for each item).
{extra}
Do not run anything that contacts Google. Reading code and running local --help is fine.

For each task, find the BEST route a competent agent could take with this tool alone, starting from a known document ID and a target described in document terms. Then grade:

coverage — exactly one of:
- native: the route achieves the outcome, scoped to the requested target, and the traced Google requests overwrite or drop nothing that ACCEPTANCE §2 says must survive for the items involved. For reads: the output actually contains the requested content/properties with their relationships.
- lossy: the route achieves the core outcome, but the code shows it changes or drops something that must survive (paragraph style reset, flattened table, link removed, comment detached, collaborator edit overwritten, property missing from read output). Name the loss in the note and cite the line.
- cannot-target: a route makes the change but cannot confine it to the requested target (replace-all only, silently first match with no way to choose, whole-tab rewrite for a local change when nothing narrower exists).
- no-route: nothing in the tool achieves the outcome, including by composing commands or raw request passthrough. A tool that safely refuses but cannot complete the task is no-route; say "refuses safely" in the note. A command that is broken at this version (e.g. always errors) does not count as a route.
For tasks tagged concurrent or lost-response, the condition is part of the outcome: silently overwriting the collaborator's change or duplicating work is lossy.

route — the ordered tool invocations (CLI subcommands or MCP tool calls) on that best route; empty for no-route. Use the canonical command name only, e.g. "edit", "cat", "docs update", "drive share", "modify_doc_text", without flags or arguments. Include discovery calls needed to find the target, IDs or indices. Mark optional=true for calls needed only sometimes (e.g. when the tab must be identified first). Exclude verification reads unless the route cannot proceed without them. When gog's raw "api call" is the only route, use it and flag caller-mechanics.

flags — caller-mechanics when the caller must supply indices, raw request bodies or other Google API details; depends-on-google when the grade hinges on Google behavior the code cannot settle (state your best reading in the note).

evidence — 1–3 citations to the specific lines that decide the grade. For no-route, cite where the absence shows (the command list, the request builder that lacks the field) or explain in the note if absence cannot be cited.

Be specific and terse. Grade every task you are given, in order, with the exact task id.
