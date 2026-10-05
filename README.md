# Google Docs agent tools: gog, Claude native and Codex native

How well three ways of letting an AI assistant work in Google Docs handle everyday document tasks, measured in October 2026:

- **gog**: the [gogcli](https://github.com/openclaw/gogcli) command-line tool (v0.35.0), driven by Claude Code.
- **Claude native**: the Google Docs and Google Drive connectors in Claude (claude.ai, Cowork and Claude Code). Google hosts them.
- **Codex native**: OpenAI's Google Drive app, used by both Codex and ChatGPT.

**Review site:** <https://alejoacelas.github.io/google-docs-agent-tools/> has the capability matrix (every task, route and piece of evidence) and the [end-to-end runs](https://alejoacelas.github.io/google-docs-agent-tools/e2e.html).

## Results

**Capability.** We graded 1,238 everyday tasks by the best route a competent agent could take with each tool:

| | gog | Claude native | Codex native |
|---|---|---|---|
| Fully supported | 1,126 (91%) | 1,111 (90%) | 993 (80%) |
| Supported, but loses something that should survive | 81 | 69 | 124 |
| Can't confine the change to the requested target | 0 | 1 | 4 |
| No route | 31 | 57 | 117 |
| Suggestion tasks fully supported (of 74) | 71 | 71 | 11 |
| File and sharing tasks fully supported (of 57) | 53 | 38 | 43 |

**End to end.** Real assistants did 90 concrete tasks on synthetic documents. We graded each run by inspecting the document afterwards:

| Setup | Pass | Partial | Fail | Median time per task |
|---|---|---|---|---|
| Claude Code + Claude native | 77 / 88 | 6 | 4 (+1 asked a question) | 33 s |
| Codex + Codex native | 69 / 88 | 7 | 12 | 75 s |
| Claude Code + gog | 69 / 89 | 7 | 13 | 30 s |

**Web apps versus their command-line twins.** We ran 30 tasks through each pair to check whether the command-line tool behaves like the web app:
- **Cowork vs Claude Code:** the same outcome on 29 of 30 tasks.
- **ChatGPT vs Codex:** the same outcome on 22 of 29, with ChatGPT doing worse: 16 passes against 23. Codex's results therefore flatter ChatGPT.

## Repository

| Path | Contents |
|---|---|
| [METHODOLOGY.md](METHODOLOGY.md) | How the tasks, grades and runs were produced, and which file each number comes from |
| [`docs/`](docs) | The hosted review site and its data: `matrix.json` (capability grades) and `e2e.json` (end-to-end outcomes) |
| [`data/`](data) | The task taxonomy, task definitions, tool definitions as captured, live probe logs and the grading prompts |
| [`pipeline/`](pipeline) | The scripts as they were run, with local paths and accounts replaced |

All documents in the tests were synthetic. Document IDs, account names and emails have been removed.
