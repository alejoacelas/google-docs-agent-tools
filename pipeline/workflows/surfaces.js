export const meta = {
  name: 'tool-matrix-surfaces',
  description: 'Map each tool\'s document-facing commands from source at the installed version',
  phases: [{ title: 'Map', detail: 'one agent per tool writes a command inventory' }],
}
const ROOT = '~/best/tools/active/gdoc/design-review'
const OUT = `${ROOT}/.supervise/tool-matrix`
const TOOLS = args
phase('Map')
const res = await parallel(TOOLS.map(t => () => agent(`Write a reference inventory of ${t.name}'s Google Docs and Drive surface, read from source code only. Other agents will use it to grade hundreds of everyday document tasks, so it must be accurate, specific and cite source lines.

Source checkout (already at the installed version ${t.version}, commit ${t.sha}): ${t.dir}
GitHub permalink base for citations: ${t.url}
Earlier notes at an older pin, useful as leads only (verify against this checkout): ${t.notes}
Scope: ${t.scope}

Write the inventory to ${OUT}/surface-${t.id}.md (create the directory if needed). For every command or tool that reads or changes Docs content, comments, suggestions, tabs or Drive files/permissions, give:
- exact invocation name and key arguments/flags (how a target is chosen: text match, occurrence, index, tab, cell, heading anchor…)
- what Google requests it sends, in order, and whether a revision precondition guards each write
- what it reads back or returns to the caller
- known losses: properties it overwrites or drops (e.g. paragraph style reset, flattened tables, skipped footnotes), with file:line permalinks
- how many tool invocations an ordinary use takes, including discovery calls needed to find indices or IDs
Then a short section on cross-cutting behavior: matching rules, read representation (what Markdown/text output includes and omits), tabs handling, account selection, error/unknown-outcome reporting, and any raw-request passthrough.

Do not run any command that contacts Google. You may run local help output (e.g. --help) if the binary is installed: ${t.binary}. Keep it dense; aim for completeness over prose. Return a 5-line summary of the file you wrote.`, { label: `surface:${t.id}`, phase: 'Map' })))
return res
