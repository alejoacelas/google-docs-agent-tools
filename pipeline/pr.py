"""Grade a pull request for one tool against the existing grades, regrading only what its diff can affect.

    python3 pr.py prepare NAME --pr 72 [--tool gdoc]   check out the PR head, select tasks, write chunks and Workflow args
    python3 pr.py collect NAME [--journal PATH]         merge the delta workflow's results into the run's head grades
    python3 pr.py build NAME [--estimate]               write planning/tool-matrix/matrix-NAME.json (base beside head)

Run files live in .supervise/tool-matrix/runs/NAME/:
  run.json        tool, PR number, base and head commits, head checkout
  base.json       the tool's grades from the full run (the "before" column)
  grades.json     head grades; each records the commit (sha) it was graded at
  select.json     tasks to regrade at the current head, with the reason
  chunks/         selected tasks with their previous grade, one file per workflow agent
  args.json       Workflow args for workflows/delta.js
  estimate.json   optional estimated head grades (see ../AGENTS.md)
After a new push, run prepare again: only tasks whose cited code changed since their last grade are selected.
"""
import argparse, collections, json, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import args as A, build, collect
from taxonomy import PURPOSES, TOOLS

RUNS = A.TM / "runs"
CHUNK = 30


def git(repo, *cmd):
    return subprocess.run(["git", "-C", str(repo), *cmd], capture_output=True, text=True, check=True).stdout


def load(p, default=None):
    return json.loads(p.read_text()) if p.exists() else default


def save(p, data):
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False))


def changed_lines(repo, a, b):
    """Changed old-side line ranges per path between commits a and b; None marks a removed or renamed file."""
    out, path = collections.defaultdict(list), None
    for line in git(repo, "diff", "-U0", "-M", a, b).splitlines():
        if line.startswith("diff --git "):
            path = None
        elif line.startswith("--- "):
            path = line[6:] if line.startswith("--- a/") else None
        elif line.startswith("+++ ") and path:
            if line[4:] == "/dev/null" or line[6:] != path:
                out[path] = None
        elif line.startswith("@@") and path and out.get(path, []) is not None:
            m = re.match(r"@@ -(\d+)(?:,(\d+))? ", line)
            start, n = int(m[1]), int(m[2] if m[2] is not None else 1)
            out[path].append((start, start + max(n, 1) - 1))
    return out


def reason(g, diff, surface):
    """Why a grade made at an earlier commit may no longer hold at the head, or None."""
    if not g.get("evidence"):
        return "no cited evidence"
    for e in g["evidence"]:
        path, _, lines = e["ref"].partition("#")
        if path not in diff:
            continue
        if diff[path] is None:
            return f"cited file {path} removed or renamed"
        m = re.match(r"L(\d+)(?:-L(\d+))?", lines)
        if not m:
            return f"cited file {path} changed"
        a, b = int(m[1]), int(m[2] or m[1])
        if any(s <= b and e2 >= a for s, e2 in diff[path]):
            return f"cited lines {e['ref']} changed"
    if g["coverage"] in ("no-route", "cannot-target") and any(p in diff for p in surface):
        return "command registrations changed, so a new route may exist"
    return None


def prepare(name, pr, tool_id):
    tool = A.tools([tool_id])[0]
    run_dir = RUNS / name
    (run_dir / "chunks").mkdir(parents=True, exist_ok=True)
    src = A.SOURCE / tool["checkout"]
    git(src, "fetch", "-q", "origin", f"pull/{pr}/head")
    head = git(src, "rev-parse", "FETCH_HEAD").strip()
    head_dir = A.SOURCE / f"{tool['checkout']}-{name}"
    if head_dir.exists():
        git(head_dir, "checkout", "-q", "--detach", head)
    else:
        git(src, "worktree", "add", "-q", "--detach", str(head_dir), head)
    head_repo = subprocess.run(["gh", "pr", "view", str(pr), "-R", tool["repo"].removeprefix("https://github.com/"),
                                "--json", "headRepositoryOwner,headRepository", "-q",
                                '.headRepositoryOwner.login+"/"+.headRepository.name'],
                               capture_output=True, text=True, check=True).stdout.strip()
    run = {"name": name, "tool": tool["id"], "pr": pr, "base_sha": tool["sha"], "head_sha": head,
           "head_repo": f"https://github.com/{head_repo}", "head_dir": str(head_dir)}
    save(run_dir / "run.json", run)

    if not (run_dir / "base.json").exists():
        base = [{**g, "sha": tool["sha"]} for g in load(A.TM / "grades.json") if g["tool"] == tool["id"]]
        save(run_dir / "base.json", base)
    current = {g["task"]: g for g in load(run_dir / "grades.json") or load(run_dir / "base.json")}
    tasks = load(A.TM / "tasks.json")
    surface = tool.get("surface_files", [])
    diffs, select = {}, {}
    for t in tasks:
        g = current.get(t["id"])
        if not g:
            select[t["id"]] = "no earlier grade"
            continue
        if g["sha"] == head:
            continue
        if g["sha"] not in diffs:
            diffs[g["sha"]] = changed_lines(head_dir, g["sha"], head)
        why = reason(g, diffs[g["sha"]], surface)
        if why:
            select[t["id"]] = why
    save(run_dir / "select.json", select)

    for old in (run_dir / "chunks").glob("chunk-*.json"):
        old.unlink()
    chunks = []
    for pid, *_ in PURPOSES:
        ids = [t["id"] for t in tasks if t["purpose"] == pid and t["id"] in select]
        for i in range(0, len(ids), CHUNK):
            rows = []
            for tid in ids[i:i + CHUNK]:
                t, g = next(x for x in tasks if x["id"] == tid), current.get(tid)
                rows.append({**{k: t[k] for k in ("id", "item", "purpose", "sentence", "tags")},
                             "why_regrade": select[tid],
                             "previous_sha": g and g["sha"],
                             "previous": g and {k: g[k] for k in ("coverage", "route", "flags", "note", "evidence")}})
            chunks.append({"file": str(run_dir / f"chunks/chunk-{len(chunks):02d}.json"), "purpose": pid, "tasks": len(rows),
                           "previous": {r["id"]: r["previous"] and {k: r["previous"][k] for k in ("coverage", "route")} for r in rows}})
            save(pathlib.Path(chunks[-1]["file"]), rows)

    url = A.blob(tool, head, run["head_repo"])
    inventory = (f"Command inventory written at the base commit {tool['sha'][:7]}: {A.TM}/surface-{tool['id']}.md. "
                 "Read it first, but the pull request may add, rename or change commands and flags; check them in the head's source.")
    save(run_dir / "args.json", {
        "run": name, "pr": pr, "head_sha": head, "head_dir": str(head_dir), "tool": tool["id"],
        "rubric": A.rubric(tool, dir=head_dir, sha=head, url=url, inventory=inventory),
        "schema": A.SCHEMA, "chunks": chunks})
    reasons = collections.Counter(r.split(" ")[0] + " " + r.split(" ")[1] for r in select.values())
    print(f"{len(select)} of {len(tasks)} tasks to regrade at {head[:7]} in {len(chunks)} chunks; "
          f"{len(tasks) - len(select)} keep their grade. Reasons: {dict(reasons)}")
    print(f"Workflow: scriptPath {HERE / 'workflows/delta.js'}, args from {run_dir / 'args.json'}")


def required(g):
    return [s["command"] for s in g.get("route", []) if not s["optional"]]


def moved(g, prev):
    """A grade moved when its coverage or required route differs from the previous grade (same rule as delta.js)."""
    return not prev or g["coverage"] != prev["coverage"] or required(g) != required(prev)


def collect_run(name, journal=None):
    run_dir = RUNS / name
    run = load(run_dir / "run.json")
    journal = journal or collect.find_journal(f"delta:{name}:")
    _, results = collect.read(journal)
    graded, verified = {}, {}
    for label, r in results:
        stage, _, chunk = label.split(":")
        target = graded if stage == "delta" else verified if stage == "dverify" else None
        if target is not None:
            for x in r["results"]:
                target[x["task"]] = x
    previous = {}
    for f in (run_dir / "chunks").glob("chunk-*.json"):
        for row in load(f):
            previous[row["id"]] = row["previous"]
    current = {g["task"]: g for g in load(run_dir / "grades.json") or load(run_dir / "base.json")}
    counts = collections.Counter()
    for tid, x in graded.items():
        if tid not in previous:
            continue
        if tid in verified:
            g, stage = verified[tid], "verified"
        elif not moved(x, previous[tid]):
            g, stage = x, "verified"  # agrees with a verified earlier grade
        else:
            g, stage = x, "graded"
        current[tid] = {**g, "tool": run["tool"], "stage": stage, "sha": run["head_sha"]}
        counts["moved" if moved(g, previous[tid]) else "kept"] += 1
        counts[stage] += 1
    save(run_dir / "grades.json", list(current.values()))
    print(f"{len(graded)} of {len(previous)} selected tasks regraded ({counts['kept']} kept, {counts['moved']} moved); "
          f"{len(verified)} re-checked by the optional verifier. From {journal}")


def build_run(name, estimate=False):
    run_dir = RUNS / name
    run = load(run_dir / "run.json")
    select = load(run_dir / "select.json")
    base = load(run_dir / "base.json")
    head_tool = f"{run['tool']}@{name}"
    tool = next(t for t in TOOLS if t["id"] == run["tool"])
    tools = [{**tool, "name": f"{tool['name']} base"},
             {**tool, "id": head_tool, "name": f"PR #{run['pr']}", "pin": f"head · {run['head_sha'][:7]}"}]
    head = {}
    for g in load(run_dir / "grades.json") or base:
        if g["sha"] == run["head_sha"] or g["task"] not in select:
            head[g["task"]] = g
    estimated = 0
    if estimate:
        est = {g["task"]: g for g in load(run_dir / "estimate.json", [])}
        for tid in select:
            if tid in head:
                continue
            prev = est.get(tid) or next((g for g in load(run_dir / "grades.json") or base if g["task"] == tid), None)
            if prev:
                head[tid] = {**prev, "stage": "estimated"}
                estimated += 1
    results = base + [{**g, "tool": head_tool} for g in head.values()]
    timings = load(A.TM / "latency/timings.json", [])
    latency = [l for l in timings if l["tool"] == run["tool"]]
    latency += [{**l, "tool": head_tool} for l in latency]
    data = build.assemble(tools, results, latency=latency, definitions=[])
    data["run"] = {"name": name, "pr": run["pr"], "base_sha": run["base_sha"], "head_sha": run["head_sha"],
                   "regrade": len(select), "estimated": estimated}
    out = HERE.parent / f"matrix-{name}.json"
    save(out, data)
    print(f"{len(head)} head grades ({estimated} estimated) beside {len(base)} base grades -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["prepare", "collect", "build"])
    ap.add_argument("name")
    ap.add_argument("--pr", type=int)
    ap.add_argument("--tool", default="gdoc")
    ap.add_argument("--journal", type=pathlib.Path)
    ap.add_argument("--estimate", action="store_true")
    a = ap.parse_args()
    if a.what == "prepare":
        prepare(a.name, a.pr, a.tool)
    elif a.what == "collect":
        collect_run(a.name, a.journal)
    else:
        build_run(a.name, a.estimate)
