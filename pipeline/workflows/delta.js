export const meta = {
  name: 'tool-matrix-delta',
  description: 'Regrade the tasks a pull request can affect against their previous grades (optional re-check of moved grades with args.verify)',
  phases: [
    { title: 'Regrade', detail: 'one agent per chunk of ~30 selected tasks grades the PR head, starting from each task\'s previous grade' },
    { title: 'Verify', detail: 'only with args.verify: one skeptical agent per chunk re-checks grades whose coverage or required route moved' },
  ],
}

// args come from `pr.py prepare NAME` (runs/NAME/args.json).
const { run, pr, head_sha, head_dir, rubric, schema: BATCH, chunks } = args

const required = (g) => (g.route || []).filter((s) => !s.optional).map((s) => s.command).join(' > ')
// Same rule as pr.py's moved(): coverage or required route differs from the previous grade.
const moved = (g, prev) => !prev || g.coverage !== prev.coverage || required(g) !== required(prev)

const DELTA = (c) => `${rubric}

This is a regrade of pull request #${pr} at its head commit ${head_sha}. The tasks are in ${c.file} (purpose: ${c.purpose}). Read that file.
Each row carries the task's previous grade ("previous"), the commit it was made at ("previous_sha"), and why it was selected ("why_regrade"). Previous grades were verified at their commit.
For each task:
- See what changed with \`git -C ${head_dir} diff <previous_sha> ${head_sha} -- <path>\` for the cited paths, and read the head source around them.
- Grade the task at the head by the rubric above. Do not anchor on the previous grade: a pull request can remove a loss, add a loss, add a route, or turn a route into a refusal. When the change does not affect the grade, keep the previous coverage and route and re-cite the evidence at the head's line numbers.
- Check for new commands or flags that make a better route, since the inventory predates the pull request.
Return results for every task in the file, with the exact task ids; set changes to "".`

const VERIFY = (c, items) => `${rubric}

You are the skeptical verifier for a regrade of pull request #${pr} at its head commit ${head_sha}. Another agent changed the grades below from their previous, verified grades (the full previous grades, with notes and evidence, are in the chunk file). For each task, decide from the head source (${head_dir}) whether the new grade or the previous one is right, or whether both are wrong:
- For an upgrade: check that the PR really removes the loss or adds the route, end to end, and that the new route does not overwrite or drop anything else (style resets, Markdown re-parsing, link/comment/footnote loss, first-tab defaults, missing revision checks under concurrent edits).
- For a downgrade: check that the head really loses what the previous grade relied on, and look for a route the grader missed, including composing commands, new flags and new subcommands. A safe refusal with no other route is no-route.
- Check that every command exists with that name at the head and that every citation points at head lines that support the claim.
The task sentences are in ${c.file}. Use \`git -C ${head_dir} diff <previous_sha> ${head_sha}\` to see what changed.
Return the corrected grade for exactly these tasks (same ids) and summarize what you changed in "changes".

${JSON.stringify(items)}`

log(`${chunks.reduce((n, c) => n + c.tasks, 0)} tasks in ${chunks.length} chunks for run ${run}`)

const out = await pipeline(
  chunks,
  (c, _, i) => agent(DELTA(c), { label: `delta:${run}:${String(i).padStart(2, '0')}`, phase: 'Regrade', schema: BATCH }),
  async (graded, c, i) => {
    if (!graded) return null
    const prev = c.previous  // previous coverage and route per task; the full previous grade is in the chunk file
    const movedItems = graded.results
      .filter((x) => moved(x, prev[x.task]))
      .map((x) => ({ task: x.task, previous: prev[x.task] || null, new: x }))
    // The skeptical re-check is off by default (see AGENTS.md); pass verify: true to run it.
    if (!movedItems.length || !args.verify) return { chunk: i, results: graded.results, verified: [], changes: '' }
    const v = await agent(VERIFY(c, movedItems), { label: `dverify:${run}:${String(i).padStart(2, '0')}`, phase: 'Verify', schema: BATCH })
    return { chunk: i, results: graded.results, verified: v ? v.results : [], changes: v ? v.changes : 'verifier returned nothing' }
  },
)

const missing = out.map((r, i) => (r ? null : i)).filter((i) => i !== null)
if (missing.length) log(`Chunks with no result: ${missing.join(', ')}`)
const movedCount = out.reduce((n, r) => n + (r ? r.verified.length : 0), 0)
log(`${movedCount} moved grades re-checked. Run: python3 pr.py collect ${run}`)
return { changes: out.filter(Boolean).map((r) => ({ chunk: r.chunk, changes: r.changes })), missing }
