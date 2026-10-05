export const meta = {
  name: 'tool-matrix-grade',
  description: 'Grade everyday Docs tasks for each tool from source, or from definitions and probes for the native connector (optional skeptical re-check with args.verify)',
  phases: [
    { title: 'Grade', detail: 'one agent per tool × chunk of ~30 tasks reads source and grades coverage, route and evidence' },
    { title: 'Verify', detail: 'only with args.verify: one skeptical agent per batch re-checks every grade' },
  ],
}

const TM = '~/best/tools/active/gdoc/design-review/.supervise/tool-matrix'
// Rubric and result schema come from grading/ via args.py, shared with pull-request runs.
const { tools, purposes, schema: BATCH } = args
const RUBRIC = (t) => t.rubric

// args.group > 1 gives each agent several consecutive chunks (used for the native connector,
// whose grading reads a probe log and tool definitions rather than source).
const GROUP = args.group || 1
const chunkFile = (i) => `${TM}/chunks/chunk-${String(i).padStart(2, '0')}.json (purpose: ${purposes[i]})`
function taskBlock(i) {
  const ids = [...Array(GROUP).keys()].map((k) => i + k).filter((k) => k < purposes.length)
  return ids.length === 1 ? `The tasks are in ${chunkFile(i)}. Read that file.` : `The tasks are in these files; read all of them:\n${ids.map(chunkFile).join('\n')}`
}

const jobs = []
for (const t of tools) for (let i = 0; i < purposes.length; i += GROUP) jobs.push({ t, i })
log(`${jobs.length} grading batches (${tools.length} tools × ${Math.ceil(purposes.length / GROUP)} groups of chunks)`)

const out = await pipeline(
  jobs,
  (_, j) => agent(`${RUBRIC(j.t)}\n\n${taskBlock(j.i)}\nReturn results for every task in the file; set changes to "".`,
    { label: `grade:${j.t.id}:${j.i}`, phase: 'Grade', schema: BATCH }),
  // The skeptical re-check is off by default: on the first full run it changed the
  // coverage level of about 3% of grades, at the cost of doubling the agents.
  (graded, j) => !graded ? null : !args.verify
    ? { tool: j.t.id, chunk: j.i, results: graded.results, changes: '', graded: graded.results.length }
    : agent(`${RUBRIC(j.t)}\n\n${taskBlock(j.i)}

You are the skeptical verifier. Another agent produced the grades below. Re-check every one against the source rather than trusting it:
- For native: look hard for anything the route overwrites or drops (style resets, Markdown re-parsing, link/comment/footnote loss, first-tab defaults, missing revision checks under concurrent edits, read output omitting the requested property). Downgrade if found.
- For no-route and cannot-target: look for a route the grader missed, including composing commands, flags, other subcommands, and raw passthrough.
- Check the route's invocation count and that each command exists with that name at this version and is not broken.
- Check that every citation points at lines that actually support the claim; fix or replace bad ones.
Return the full corrected list (every task, same ids) and summarize what you changed in "changes".

Grader output:
${JSON.stringify(graded.results)}`,
    { label: `verify:${j.t.id}:${j.i}`, phase: 'Verify', schema: BATCH }).then(v => v && ({ tool: j.t.id, chunk: j.i, results: v.results, changes: v.changes, graded: graded.results.length })),
)

const results = [], changes = [], missing = []
out.forEach((r, k) => {
  if (!r) { missing.push(`${jobs[k].t.id}:${jobs[k].i}`); return }
  for (const x of r.results) results.push({ ...x, tool: r.tool })
  changes.push({ tool: r.tool, chunk: r.chunk, changes: r.changes })
})
if (missing.length) log(`Batches with no result: ${missing.join(', ')}`)
return { results, changes, missing }
