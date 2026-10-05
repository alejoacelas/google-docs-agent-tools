# Methodology

There are two layers. The **capability matrix** asks what each tool makes possible, independent of any model. The **end-to-end runs** ask what real assistants actually do with it. Every result came from synthetic Google Docs, between 2 and 5 October 2026.

## The tools and the accounts

| | What was tested | Account used |
|---|---|---|
| gog | gogcli v0.35.0 at commit `402def5` | Gmail account |
| Claude native | claude.ai's Google Docs (`read_doc`, `update_doc`) and Google Drive (11 tools) connectors | Google Workspace account |
| Codex native | OpenAI's Google Drive app (45 tools; the same app powers ChatGPT) | Gmail account |

- **Why the accounts differ:** each connector ran on the account it was already connected to.
- **Effect on results:** nearly all tasks behave the same on Gmail and Workspace. The exceptions are shared drives and organization-wide sharing, which were not run live.

## 1. Task catalog

There are 1,238 one-sentence tasks, each tagged with:
- **a purpose:** read, select, change wording, format, create, restructure, preserve, publish Markdown, update from Markdown, suggest, discuss or manage;
- **an item:** one of 22 document items, such as text range, heading, table, tab, footnote, comment, suggestion or file;
- **variations:** 18 tags, such as repeated wording, nested tab, inside a table cell, concurrent edit or lost response.

The vocabulary comes from [`data/ACCEPTANCE.md`](data/ACCEPTANCE.md). Its §2 lists what must survive each kind of edit. Agents generated the catalog and a critic pass removed duplicates (`pipeline/workflows/catalog.js`). The tasks are in [`docs/matrix.json`](docs/matrix.json) under `tasks`.

## 2. Capability grading

Every task gets one coverage level per tool:
- **native:** the outcome is reachable, confined to the target, and loses nothing that must survive;
- **lossy:** reachable, but something that should survive is lost;
- **cannot-target:** the change can't be confined to the requested target;
- **no-route:** no way to reach the outcome.

Each grade also records the route of tool calls, flags, and one to three pieces of evidence. The prompts are [`data/prompts/rubric.md`](data/prompts/rubric.md) for gog and [`data/prompts/rubric-native.md`](data/prompts/rubric-native.md) for the hosted connectors. Both use the schema in [`batch-schema.json`](data/prompts/batch-schema.json). Claude agents did the grading, each handling 30 to 180 tasks (`pipeline/workflows/grade.js`).

- **gog: from source.** Graders read gogcli's code at the pinned commit and cite line ranges. A second agent re-checked 1,062 grades. On the first run, that re-check changed the coverage level of about 3% of grades.
- **Hosted connectors: definitions plus live probes.** Their code is closed, so graders read:
  - the tool definitions, captured verbatim in [`data/tools/`](data/tools);
  - a log of 57 live probes for each connector ([`data/probes/`](data/probes)). Each probe tests one behaviour that many tasks depend on: for example, whether replacing words inside a linked, commented phrase keeps the link and the comment, or whether a read returns pending suggestions. Up to three agent workers ran the probes ([`data/prompts/probe-worker.md`](data/prompts/probe-worker.md)). They acted only through the connector, on fresh copies of synthetic fixture documents, and inspected the results with a separate client.

  A probe result overrides the documentation. Each grade's note says whether a probe decided it ("probe-backed": 887 grades for Claude native, 944 for Codex native) or whether it is "predicted" from the definitions and Google's API reference.
- **Google's September 2026 Developer Preview.** The Docs API gained requests that create anchored comments, reply to and resolve them, accept or reject suggestions, and make any edit a suggestion (`writeControl.writeMode: SUGGEST`).
  - **Claude native:** a live probe showed its `update_doc` accepts them, so 114 Claude native grades were regraded.
  - **Codex native:** its `batch_update_document` accepts the comment and accept/reject requests but rejects suggestion mode.
  - **gog:** graders re-read its source, and 176 gog grades moved, because its raw `api call` command can send these requests.

  The regraded results carry `stage: "regraded"` in `matrix.json`.
- **Timings.** Only gog's commands have timings, from single commands run live five times on synthetic documents (`pipeline/latency/`). The hosted connectors run only inside an assistant session, where model time can't be separated from the call itself. The end-to-end runs give their response times instead.

## 3. End-to-end runs

**Fixtures.** Each run gets a fresh copy of a synthetic document. There are three:
- a short report with tabs (including a child tab), a footnote, a header, an image, nested lists and a table with a merged cell;
- a heavily formatted variant of it;
- a 40-section long document.

Setup then adds a standard comment and a pending suggestion, plus anything the task needs. A snapshot of the copy, taken before the run, is the ground truth for grading (`pipeline/surface/setup.py`).

**Runs.** Each task runs once, in a new session, with the prompt verbatim and no other input, except clicking an approval card when one appears. The command-line runs are isolated to one route (`pipeline/surface/run.py`):
- **Claude Code:** local Google tools and personal instruction files are excluded.
- **Codex:** runs with only its Google Drive plugin. With its browser plugins on, it opens the document in Chrome instead of using the connector.

The web apps (Cowork and ChatGPT) were driven through Chrome by an agent. Runs that strayed onto another route were set aside and rerun: Cowork reaching local tools through the paired desktop app, or a newly added local server. Models were each product's default: Opus 5.5 for Claude Code and Cowork, gpt-6-astra for Codex, and GPT-5.6 Thinking for ChatGPT.

**Grading.** A grader inspected each document after the run and compared it with the pre-run snapshot ([`data/prompts/grader.md`](data/prompts/grader.md)). For each check, the grader recorded the effect, what was preserved, and what was reported, with evidence. Outcomes:
- **pass:** everything requested happened and was reported correctly, and nothing that should survive was lost;
- **partial:** the change happened, but something was lost or misreported;
- **fail:** not done, wrong, or declined;
- **asked:** the assistant asked a question instead of acting.

When a task's check contradicted the pre-run snapshot, the grader judged by intent and marked the check "adjusted". One grader handled all configurations of a task, so the bar is the same across them.

- **Surface check:** 30 tasks ([`data/tasks/surface-tasks.json`](data/tasks/surface-tasks.json)), each run through a web app and its command-line twin on identical copies. The rule: the command-line tool can stand in for the web app if it reaches the same outcome on at least 26 of 30 tasks, with no systematic difference in tools or damage.
  - **Claude Code and Cowork:** passed (29 of 30).
  - **Codex and ChatGPT:** did not (22 of 29). So the Codex main runs describe Codex, not ChatGPT.
- **Main runs:** 90 tasks ([`data/tasks/main-tasks.json`](data/tasks/main-tasks.json)) mirroring catalog tasks across all twelve purposes, run in three setups: Claude Code + Claude native, Codex + Codex native, and Claude Code + gog. One task (m16) could not be set up. Some setup steps did not produce the intended state; graders judged against the snapshot and noted it.

## How the numbers connect to the files

| Number | Source |
|---|---|
| Capability counts and per-purpose rows | `docs/matrix.json` → `results[]` where `tool` is `gog`, `native` (Claude native) or `openai` (Codex native), field `coverage`; purpose from `tasks[]` |
| Probe-backed vs predicted | the `note` field of each result; probes in `data/probes/` |
| End-to-end pass, partial and fail | `docs/e2e.json` → `configs[].outcomes`, or `results[]` filtered by `suite` and `config` |
| Median time per task | median of `results[].seconds` for that suite and configuration |
| Surface agreement (29 of 30, 22 of 29) | pairs of `results[]` in suite `surface` with the same `task` |

## Limits

- **One run per task.** End-to-end results mix the model, the app around it and the connector. The capability matrix isolates the connector.
- **Many hosted-connector grades are predicted.** Their notes say so. Developer Preview features may change before general release.
- **Times include setup overhead.** Codex's longer times come largely from its skill's read step, about 20 shell calls before each edit. Cowork's times include clicking approval cards.
- **The catalog's coverage targets come from one product's acceptance criteria.** That product is [gdoc](https://github.com/LucaDeLeo/gdoc). The tasks are generic, but the weighting across purposes reflects those criteria.
