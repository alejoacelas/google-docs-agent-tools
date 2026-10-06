# Where Claude's Google Docs connector falls short

Claude's Google Docs connector handles most everyday document work. In October 2026 we gave fresh Claude sessions ordinary requests on a synthetic project plan and inspected the document after each run. Twelve gaps came up. Most trace back to one of three sources: Google's Docs API has no request for the operation, the connector exposes less than Google's APIs offer, or Anthropic's `google-workspace` skill tells Claude something can't be done when it can.

**Full report:** [CONNECTOR-GAPS.md](CONNECTOR-GAPS.md), with what Claude did in each test, why it happens and what the runs showed.

## The gaps

| # | Gap | What goes wrong | Where it comes from |
|---|---|---|---|
| 1 | Pending suggestions | Chat states suggested text as settled fact. | Drive's `read_file_content` prints suggested and original text side by side with no markers. |
| 2 | Ticked checkboxes | Claude reports ticked items as unticked unless asked about the checklist directly. | `documents.get` doesn't return checked state; only the Markdown export does. |
| 3 | Inserting a local image | The insert fails and the user has to change sharing by hand. | `insertInlineImage` needs a public URL, and `share_file` can only share with one email address. |
| 4 | Nesting a list item | Claude fakes nesting with indentation or asks the user to press Tab. Chat restyles the whole list. | The Docs API has no request to change an item's nesting level. |
| 5 | Accepting or rejecting suggestions; replying to or resolving comments | Claude retypes suggestions as direct edits and says replies are impossible. | The skill says so, but `update_doc` already accepts Google's preview requests for all four. |
| 6 | Editing text that has a comment | The comment can end up covering only part of the new text. | A comment keeps only the original characters that survive an edit. |
| 7 | Version history | Claude can't say what the doc said earlier. | No tool lists revisions or downloads an old one. |
| 8 | Moving a section | Claude asks the user to cut and paste. | No move request exists; delete and retype loses comments and suggestions. |
| 9 | Table of contents | Claude inserts a list of links that won't update. | The Docs API can't insert Google's table of contents. |
| 10 | Adding a suggestion next to an existing one | The new suggestion merges into the old one. | Docs merges touching suggestions from the same account. |
| 11 | Copying a doc | The copy loses comments and suggestions. | Drive's copy carries only the text. |
| 12 | Reading a doc | A short doc returns about 50,000 characters of JSON, more than the tool can return. | `documents.get` returns raw JSON with styling for every text run and nine nesting levels for every list. |

Gaps 1–4 are the ones first noticed in everyday use. Updating a doc from edited Markdown held up in these tests.

## How we tested

- **Fixture:** one synthetic project plan with three comments, two pending suggestions, a checklist with two items ticked, a nested list, a header, a link to a heading and a table with fixed column widths.
- **Requests:** 14 one-sentence requests a person might type, such as "Which items on the launch checklist are still open?" or "Move the Risks section up so it comes right after the Summary."
- **Claude Code:** 28 runs, two per request, each a new session with Opus 5.5 and only the Google Docs and Drive connectors available.
- **Claude chat on claude.ai:** 7 runs on five of the requests.
- **Grading:** each run got a fresh copy of the fixture. We compared a snapshot of the document taken before and after the run, and read Claude's reply.

## Replicating

[`connector-gaps/REPLICATING.md`](connector-gaps/REPLICATING.md) walks through building the fixture, running the requests in Claude Code and chat, and grading the results. The pieces:

- [`connector-gaps/data/`](connector-gaps/data): the requests with their pass criteria, the fixture, and every run's prompt, tool calls, time, reply, document diff and verdict.
- [`connector-gaps/harness/`](connector-gaps/harness): the scripts as run, with accounts and document IDs removed.

You need a Google account connected to Claude's Google Docs and Drive connectors, Claude Code, and Python with Google API access to the same account to build fixtures and take snapshots. We used [gdoc](https://github.com/LucaDeLeo/gdoc)'s environment. Use an unshared folder: the image test uploads a file to Drive.

## Earlier comparison: gog, Claude native and Codex native

Before these tests we compared three ways of letting an assistant work in Google Docs on 1,238 catalogued tasks and 90 end-to-end runs. Claude Code with Claude's connectors passed 77 of 88 end-to-end tasks, Codex with OpenAI's Google Drive app 69 of 88, and Claude Code with the [gogcli](https://github.com/openclaw/gogcli) command-line tool 69 of 89. Most of the difference came from suggestions and comments.

- **Review site:** <https://alejoacelas.github.io/google-docs-agent-tools/> has the capability matrix and the [end-to-end runs](https://alejoacelas.github.io/google-docs-agent-tools/e2e.html).
- **Method:** [METHODOLOGY.md](METHODOLOGY.md) explains how the tasks, grades and runs were produced, and which file each number comes from.

## Repository

| Path | Contents |
|---|---|
| [CONNECTOR-GAPS.md](CONNECTOR-GAPS.md) | The connector-gaps report |
| [`connector-gaps/`](connector-gaps) | Data, harness and replication guide for the connector-gaps tests |
| [METHODOLOGY.md](METHODOLOGY.md) | Method for the earlier comparison |
| [`docs/`](docs) | The review site and its data (`matrix.json`, `e2e.json`) |
| [`data/`](data) | Task taxonomy, task definitions, tool definitions, probe logs and grading prompts for the comparison |
| [`pipeline/`](pipeline) | The comparison's scripts as run |

All test documents were synthetic. Document IDs, account names and emails have been removed.
