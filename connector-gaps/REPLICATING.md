# Replicating the connector-gaps runs

These runs check how Claude's Google Docs and Drive connectors handle 14 ordinary requests on a realistic document. Each run builds a fresh copy of one synthetic project plan, sends one plain request to a new Claude session, and then compares the document before and after.

## What you need

- A Google account connected to Claude's **Google Docs** and **Google Drive** connectors on claude.ai. Claude Code uses the same connectors.
- Python with Google API access to that same account, used to build fixtures and take snapshots. We used [gdoc](https://github.com/LucaDeLeo/gdoc)'s Python environment and its `gdoc` CLI. The harness calls `gdoc mkdir`, `comment`, `suggest`, `edit` and its Docs and Drive clients. Any client that can make the same calls works.
- Claude Code, for the scripted runs. We used Opus 5.5, Claude Code's default on 6 October 2026.

## The fixture

[`data/fixture.md`](data/fixture.md) is imported through Google's own Markdown import, as a person uploading a `.md` file would. The import already makes the checklist with two items ticked, and a nested list under Next steps. The harness then adds what Markdown can't express (`build()` in `harness/gaps.py`, `enrich()` in `harness/harness.py`):

1. A page header: "Onboarding pilot · internal".
2. An empty paragraph above the Results heading, and a link from "Results section" to that heading.
3. Fixed column widths (180, 90 and 110 pt) on the Milestones table.
4. Three comments:
   - "This feels vague…" on the two-weeks sentence;
   - "Does this include tax?" on "$12,500";
   - "Can we ask their manager to delegate approvals?" on "Two pilot teams share a manager".
5. Two pending suggestions:
   - "…delivery date." → "…delivery date if the vendor's warehouse move slips.";
   - "$4,000" → "$5,500".

The history task also edits "Kickoff: Monday 6 October" to "Tuesday 14 October" four minutes after the build, and then retakes the "before" snapshot.

All the comments and suggestions come from the same account that Claude uses. Google merges adjacent suggestions by the same author, which the suggest-adjacent task depends on.

## Claude Code runs

```
GAPS_ACCOUNT=[email] GAPS_WORKDIR=/tmp/gaps-work \
  python harness/gaps.py run summary,budget,checklist 2 3     # tasks, runs per task, parallel sessions
```

Each run gets its own document, Drive folder and working directory. `GAPS_WORKDIR` must be outside any repository, so that no project instructions load. Each run is a new `claude -p` session with:
- `--disallowedTools` for everything except the Docs and Drive connectors: local Google servers, other hosted Google servers, Chrome and computer use, and Gmail, Calendar and Slack, so that no run can message anyone;
- personal `CLAUDE.md` and `AGENTS.md` files excluded;
- local Google CLIs shadowed on `PATH`. `curl` and `wget` are wrapped to refuse uploads, so no run can publish the image task's chart.

Only the Google Docs and Drive connectors, Anthropic's built-in skills and ordinary shell tools remain. The image task writes `results-chart.png` into the working directory first.

The harness saves, for each run:
- the transcript (`stream-json`);
- snapshots of `documents.get` (with comments and comment anchors) and of the comment list, before and after;
- a text diff covering the body, lists and bullet glyphs, comment anchors and pending suggestions.

## Claude chat runs

These were run by hand in claude.ai chat, with Opus 5.5 and the Docs and Drive connectors on. `harness/chat_prompt.py RUN` prints a snippet that pastes the task's prompt into a new chat and sends it. Then:
1. Approve any connector cards that appear, and give no other input.
2. When the reply is finished, take the "after" snapshot with `python harness/gaps.py snap RUN`.

Turn off any other Google connector you have in the composer's Connectors menu. In two of our runs Claude used our own Google API connector instead (marked `off-route` or noted in `data/runs.json`). Chat can also reach Claude in Chrome when it is installed, and one run used it to accept a suggestion through the Docs UI.

## Grading

Each run was graded by reading its diff and its final reply against the task's `pass` line in [`data/tasks.json`](data/tasks.json). The scale is at the top of `data/runs.json`: pass, partial, fail, asked or off-route. A reply that discloses a loss still counts as partial or fail, because the requested effect didn't happen.

## Known quirks

- **Missing "before" comments in older diffs.** In most published diffs, "comments before" is empty. The comment listing lagged just after the comments were created, so the "before" snapshot missed them. The fixture always has the three comments (see "comments after" on unchanged runs). The harness now waits briefly before that snapshot.
- **Personal Gmail account.** All runs used one. Shared drives and domain sharing were not tested.
- **Run counts.** Each Claude Code task ran twice and each chat task once or twice. Read the counts as numbers of runs, not rates.
