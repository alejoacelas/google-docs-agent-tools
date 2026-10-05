export const meta = {
  name: 'tool-matrix-catalog',
  description: 'Draft and critique day-to-day Google Docs tasks for every item × purpose cell of the tool matrix',
  phases: [
    { title: 'Draft', detail: 'one agent per purpose drafts tasks for every applicable item' },
    { title: 'Critique', detail: 'one critic per purpose filters, splits, merges and fills gaps' },
  ],
}

const ROOT = '~/best/tools/active/gdoc/design-review'
const { purposes, items, applicable, tags } = args

const TASK_SCHEMA = {
  type: 'object',
  properties: {
    tasks: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          item: { type: 'string', description: 'item id from the provided list' },
          purpose: { type: 'string', description: 'purpose id from the provided list' },
          sentence: { type: 'string', description: 'one plain atomic imperative sentence' },
          tags: { type: 'array', items: { type: 'string' } },
          context: { type: 'string', description: 'under 15 words: the everyday situation this comes from' },
        },
        required: ['item', 'purpose', 'sentence', 'tags', 'context'],
      },
    },
    notes: { type: 'string', description: 'short notes on judgment calls, moved or dropped tasks' },
  },
  required: ['tasks', 'notes'],
}

const itemList = items.map(i => `- ${i.id}: ${i.label} — ${i.hint}`).join('\n')
const tagList = tags.map(t => `- ${t.id}: ${t.label}`).join('\n')
const purposeList = purposes.map(p => `- ${p.id}: ${p.label} — ${p.outcome}`).join('\n')

const RULES = `
What we are building: a catalog of tasks against which three Google Docs tools for agents (gdoc, Taylor's Workspace MCP, gog) will each be graded by reading their code. The grid aggregates tasks by document item (rows) × purpose (columns), taken from ${ROOT}/planning/ACCEPTANCE.md §§2–3. Each task is graded independently, so each must be a distinct, gradeable outcome.

Rules for every task:
1. Day-to-day work. Include only things people (or their agents) plausibly do in ordinary work with shared Google Docs: drafting reports, publishing notes, editing proposals, reviewing with comments and suggestions, maintaining docs with collaborators. A sentence containing emoji is fine; a test of a specific exotic character that triggers a bug is not. Ordinary messy conditions belong in: repeated phrases, nested tabs, tables, comments on the text, a collaborator editing at the same time, long documents.
2. One plain atomic sentence, imperative, in document terms ("Change the date in the second table's header row."). No tool names, API terms, indices, request types, or test jargon. One outcome per sentence; no "and then". Up to ~20 words.
3. Comprehensive within those constraints. Cover the common variants of each applicable item for this purpose: different containers and locations (body, nested tab, table cell, footnote, header), common relationships (links, comments, suggestions, list nesting), and common conditions. Rare items (equations, drawings, charts) get fewer tasks than common ones (paragraphs, headings, tables, comments). Roughly 3–12 tasks per applicable item, chosen by how often the situation arises, not to fill a quota.
4. "Preserve" tasks are phrased as keeping something while another everyday change happens nearby or across it ("Keep a footnote attached to its sentence when rewording that sentence.").
5. Tags: use only these ids, and only when the task genuinely involves the condition:
${tagList}
6. Items:
${itemList}
7. Purposes:
${purposeList}

Useful context (read what helps):
- ${ROOT}/planning/ACCEPTANCE.md — the taxonomy, item properties, and §5 structural actions table.
- ${ROOT}/planning/PRODUCT-BRIEF.md — the three core tasks.
- ${ROOT}/reference-only/inputs/USER-TASKS-AND-PRIORITIES.md — real usage episodes (synthetic examples); best evidence of day-to-day demand.
- ${ROOT}/planning/TEST-ORGANIZATION.md — how families and situations are chosen.
- ${ROOT}/coverage/wording/CATALOG.md — an existing family of wording tasks; reuse its everyday situations, drop its diagnostic edge cases.
Do not run any Google operation or tool CLI. Read files only.`

function draftPrompt(p) {
  const its = applicable[p.id].map(id => items.find(i => i.id === id)).map(i => `${i.id} (${i.label})`).join(', ')
  return `${RULES}

Your assignment: draft every task for purpose "${p.id}" (${p.label}). Applicable items: ${its}.
Every task you return must have purpose "${p.id}" and one of those item ids. If a task belongs more naturally to another item, use that item if it is in the list; otherwise drop it and mention it in notes.`
}

function critiquePrompt(p, draft) {
  const its = applicable[p.id].join(', ')
  return `${RULES}

You are the critic for purpose "${p.id}" (${p.label}); applicable items: ${its}.
Below is a drafted task list. Return the corrected final list:
- Drop tasks that are not day-to-day work, that test a contrived edge case, or that are not gradeable.
- Split any sentence that contains two outcomes; tighten wording to plain document terms.
- Merge near-duplicates (same outcome, trivially different wording).
- Fix wrong item ids or tags.
- Add missing everyday tasks: walk each applicable item and ask what someone working on a shared doc most often needs for this purpose that is absent. This completeness pass matters as much as the filtering.
In notes, summarize what you dropped, merged and added (counts and one-line reasons).

Drafted list (JSON):
${JSON.stringify(draft.tasks)}

Drafter notes: ${draft.notes}`
}

const results = await pipeline(
  purposes,
  p => agent(draftPrompt(p), { label: `draft:${p.id}`, phase: 'Draft', schema: TASK_SCHEMA }),
  (draft, p) => draft && agent(critiquePrompt(p, draft), { label: `critic:${p.id}`, phase: 'Critique', schema: TASK_SCHEMA }),
)

const out = []
const notes = {}
purposes.forEach((p, i) => {
  const r = results[i]
  if (!r) { log(`No result for ${p.id}`); return }
  notes[p.id] = r.notes
  for (const t of r.tasks) {
    if (t.purpose !== p.id || !applicable[p.id].includes(t.item)) { log(`Dropped misfiled task in ${p.id}: ${t.sentence}`); continue }
    out.push(t)
  }
})
return { tasks: out, notes }
