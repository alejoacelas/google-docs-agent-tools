"""Naturalistic checks of gaps in Claude's Google Docs connector.

Each run builds a fresh synthetic plan in the the organization account (unshared folder), asks a clean
Claude Code session one ordinary request, then snapshots and diffs the document.
Run with gdoc's Python (first line of `which gdoc`). IDs, transcripts and snapshots
stay in .supervise/connector-gaps/.

    python gaps.py build RUN TASK        build RUN's document, snapshot "before"
    python gaps.py run TASK [N] [JOBS]   build and run N Claude Code sessions for TASK
    python gaps.py snap RUN              snapshot "after"
    python gaps.py diff RUN              print what changed
    python gaps.py edit-kickoff RUN      the later edit the history task asks about
"""
import concurrent.futures as cf, difflib, json, os, pathlib, struct, subprocess, sys, threading, time, zlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "trap-tests"))
import harness as h  # noqa: E402  (reuses the trap tests' builders and renderers)

# The account Claude's Google connectors are signed in to (GAPS_ACCOUNT overrides).
h.ACCOUNT = os.environ.get("GAPS_ACCOUNT", "[email]")

ROOT = HERE.parents[1]
OUT = ROOT / ".supervise/connector-gaps"
RUNS = OUT / f"runs-{h.ACCOUNT.split('@')[0]}.json"
TASKS = json.loads((HERE / "tasks.json").read_text())
SHIMS = OUT / "bin"
LOCK = threading.Lock()
API = threading.Lock()  # Google's client is not thread-safe; only the Claude sessions run in parallel

BASE = h.BASE.replace("""## Results""", """## Launch checklist

- [x] Book a venue for the launch review
- [ ] Send the vendor invoice
- [x] Order the starter kits
- [ ] Legal review of the participant agreement

## Results""").replace("""- Confirm kit contents with the vendor
- Schedule the launch review""", """- Confirm kit contents with the vendor
  - Check that the welcome letters are included
- Schedule the launch review""")

# Tools outside the Google Docs and Drive connectors: local Google servers, other hosted
# Google servers, browser and computer use, and anything that could message people.
BLOCKED = ["mcp__workspace-google", "mcp__own-google-api-connector", "mcp__claude_ai_own-google-api-connector",
           "mcp__claude_ai_render_html", "mcp__claude_ai_test_two_login_option", "mcp__claude_ai_Gdoc_connector_v1",
           "mcp__claude-in-chrome", "mcp__computer-use", "mcp__claude_ai_Gmail", "mcp__claude_ai_Google_Calendar",
           "mcp__claude_ai_Slack", "mcp__claude_ai_slack-cli-mcp", "mcp__claude_ai_Resend"]


def runs():
    return json.loads(RUNS.read_text()) if RUNS.exists() else {}


def update(run, **kw):
    with LOCK:
        r = runs()
        r.setdefault(run, {}).update(kw)
        RUNS.write_text(json.dumps(r, indent=1))


def folder():
    r = runs()
    if "_folder" not in r:
        r["_folder"] = h.gdoc("mkdir", "Connector gaps (synthetic)")["id"]
        RUNS.write_text(json.dumps(r, indent=1))
    return r["_folder"]


def build(run, task):
    f = h.gdoc("mkdir", f"Run {run}", "--parent", folder())["id"]
    doc = h.import_markdown(f"Onboarding pilot — Q4 plan ({run})", BASE, f)
    h.enrich(h.svc(), doc)
    h.gdoc("comment", doc, "This feels vague. What counts as finishing onboarding?", "--quote", "We expect most teams to finish onboarding within two weeks.")
    h.gdoc("comment", doc, "Does this include tax?", "--quote", "$12,500")
    h.gdoc("comment", doc, "Can we ask their manager to delegate approvals?", "--quote", "Two pilot teams share a manager")
    h.gdoc("suggest", doc, "may miss the kit delivery date.", "may miss the kit delivery date if the vendor's warehouse move slips.")
    h.gdoc("suggest", doc, "$4,000", "$5,500")
    update(run, task=task, doc=doc, folder=f, built=time.time())
    time.sleep(10)  # the comment list lags just after creation; without this the "before" snapshot misses the comments
    snap(run, "before")
    return doc


def edit_kickoff(run):
    h.gdoc("edit", runs()[run]["doc"], "Kickoff: Monday 6 October", "Kickoff: Tuesday 14 October")
    update(run, edited=time.time())


def snap(run, label):
    data = h.raw(runs()[run]["doc"])
    (OUT / "snaps").mkdir(parents=True, exist_ok=True)
    (OUT / "snaps" / f"{run}-{label}.json").write_text(json.dumps(data))


def lists(doc_json):
    """Glyph per nesting level for every list, which h.lines does not show."""
    tab = doc_json["tabs"][0]["documentTab"]
    return [f"list {lid[-4:]}: " + " ".join(f"L{i}={lv.get('glyphType') or lv.get('glyphSymbol', '?')}" for i, lv in enumerate(l["listProperties"]["nestingLevels"][:3]))
            for lid, l in sorted(tab.get("lists", {}).items())]


def diff(run):
    b = json.loads((OUT / "snaps" / f"{run}-before.json").read_text())
    a = json.loads((OUT / "snaps" / f"{run}-after.json").read_text())
    out = [f"== {run} ({runs()[run]['task']}) revision changed: {b['doc'].get('revisionId') != a['doc'].get('revisionId')}"]
    (lb, hb), (la, ha) = h.lines(b["doc"]), h.lines(a["doc"])
    out += ["-- body/header changes:"] + ([l for l in difflib.unified_diff(lb, la, lineterm="", n=0) if not l.startswith(("---", "+++"))] or ["(none)"])
    lost = [f"{k[-6:]} {v!r}" for k, v in hb.items() if k not in ha]
    if lost:
        out.append("-- heading IDs gone: " + ", ".join(lost))
    out.append(f"-- heading links now: {sum('→#heading' in l for l in la)} (before {sum('→#heading' in l for l in lb)})")
    if lists(b["doc"]) != lists(a["doc"]):
        out += ["-- lists before:"] + lists(b["doc"]) + ["-- lists after:"] + lists(a["doc"])
    out += ["-- comments before:"] + h.anchors(b) + ["-- comments after:"] + h.anchors(a)
    out += ["-- suggestions before:"] + h.suggestions(b) + ["-- suggestions after:"] + h.suggestions(a)
    return "\n".join(out)


def png(path):
    """A small bar chart, so the image task has a real local file."""
    w, hgt, bars = 360, 220, [(40, 120, (66, 133, 244)), (130, 170, (52, 168, 83)), (220, 80, (251, 188, 5))]
    rows = []
    for y in range(hgt):
        row = bytearray([0])
        for x in range(w):
            c = (255, 255, 255)
            for bx, bh, col in bars:
                if bx <= x < bx + 70 and hgt - 20 - bh <= y < hgt - 20:
                    c = col
            if y == hgt - 20:
                c = (60, 60, 60)
            row += bytes(c)
        rows.append(bytes(row))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, hgt, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(b"".join(rows))) + chunk(b"IEND", b""))


def shims():
    """Shadow local Google CLIs; log and refuse uploads to outside hosts so no test publishes anything."""
    SHIMS.mkdir(parents=True, exist_ok=True)
    for name in ("gdoc", "gog", "workspace-mcp"):
        (SHIMS / name).write_text(f'#!/bin/sh\necho "{name}: command not found" >&2\nexit 127\n')
    for name in ("curl", "wget"):
        real = subprocess.run(["which", name], capture_output=True, text=True).stdout.strip() or f"/usr/bin/{name}"
        (SHIMS / name).write_text(f"""#!/bin/sh
for a in "$@"; do case "$a" in -F|--form*|-T|--upload-file*|-d|--data*|--post-*|-X) echo "$(date) {name} $*" >> "{OUT}/blocked-uploads.log"; echo "{name}: network uploads are disabled on this machine" >&2; exit 1;; esac; done
exec {real} "$@"
""")
    for p in SHIMS.iterdir():
        p.chmod(0o755)


def command(prompt):
    return [str(pathlib.Path.home() / ".local/bin/claude"), "-p", "--dangerously-skip-permissions", "--disallowedTools", *BLOCKED,
            "--settings", json.dumps({"claudeMdExcludes": ["**/CLAUDE.md", "**/AGENTS.md"]}),
            "--output-format", "stream-json", "--verbose", prompt]


def run_one(task_id, n, scratch):
    task = TASKS[task_id]
    run = f"{task_id}-cli-{n}"
    if runs().get(run, {}).get("exit") is not None:
        return
    with API:
        doc = build(run, task_id)
    if task_id == "history":
        time.sleep(240)
        with API:
            edit_kickoff(run)
        time.sleep(30)
        with API:
            snap(run, "before")
    work = pathlib.Path(scratch) / run
    work.mkdir(parents=True, exist_ok=True)
    if task_id == "image":
        png(work / "results-chart.png")
    prompt = task["prompt"].replace("{doc}", f"[doc-link]
    keep = [p for p in os.environ["PATH"].split(":") if ".local/bin" not in p]
    env = {**os.environ, "PATH": ":".join([str(SHIMS), *keep])}
    (OUT / "transcripts").mkdir(parents=True, exist_ok=True)
    start = time.time()
    with open(OUT / "transcripts" / f"{run}.jsonl", "w") as log:
        try:
            code = subprocess.run(command(prompt), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                  cwd=work, env=env, timeout=15 * 60).returncode
        except subprocess.TimeoutExpired:
            code = "timeout"
    with API:
        snap(run, "after")
    update(run, prompt=prompt, seconds=round(time.time() - start, 1), exit=code)
    (OUT / "diffs").mkdir(parents=True, exist_ok=True)
    with API:
        (OUT / "diffs" / f"{run}.txt").write_text(diff(run))
    print(run, code, round(time.time() - start), "s", flush=True)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "base.md").write_text(BASE)
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "build":
        print(build(args[0], args[1]))
    elif cmd == "snap":
        snap(args[0], "after")
    elif cmd == "diff":
        print(diff(args[0]))
    elif cmd == "edit-kickoff":
        edit_kickoff(args[0])
    elif cmd == "run":
        shims()
        scratch = os.environ["GAPS_WORKDIR"]  # outside any repository, so no project instructions load
        task_ids = args[0].split(",")
        n = int(args[1]) if len(args) > 1 else 2
        jobs = int(args[2]) if len(args) > 2 else 3
        with cf.ThreadPoolExecutor(jobs) as pool:
            list(pool.map(lambda a: run_one(*a, scratch), [(t, i) for t in task_ids for i in range(1, n + 1)]))
