"""Make one fresh copy of a fixture per task and surface for the surface check.

    python3 setup.py SIDE [SURFACE ...]      SIDE is claude or openai; surfaces default to cli and web

Templates come from latency/fixtures.py (FIXTURE_DIR=surface/SIDE FIXTURE_TOOLS=template).
Drive copies drop comments and suggestions, so each copy of a short or formatted fixture
gets the standard comment on "pilot teams" and the standard pending suggestion back, then
the task's setup_extra commands (gdoc arguments; DOC is the copy, COMMENT_A the standard comment).
Then saves a BASE snapshot of the copy (documents.get with suggestions inline, Markdown, comments
and file info) in SIDE/base/SURFACE/TASK/, so graders judge against the document as set up.
Surface "ref" makes untouched reference copies. TASKS (default tasks.json) and the output folder
can be changed with --tasks FILE --out DIR (for the main runs).
Writes SIDE/copies.json; reruns skip copies that exist.
"""
import concurrent.futures as cf, json, pathlib, shlex, subprocess, sys, threading

ROOT = pathlib.Path(__file__).resolve().parents[4]
SURFACE = ROOT / ".supervise/tool-matrix/surface"
COMMENT = ("Is the pilot date confirmed?", "pilot teams")
SUGGESTION = ("Open questions go here.", "Open questions and decisions go here.")


def gdoc(account, *args):
    r = subprocess.run(["gdoc", *args, "--account", account, "--json"], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"gdoc {' '.join(args[:2])}: {r.stderr.strip() or r.stdout.strip()}")
    return json.loads(r.stdout) if r.stdout.strip().startswith("{") else {}


def snapshot(account, doc, folder):
    folder.mkdir(parents=True, exist_ok=True)
    for name, args in {"structure.json": ["structure", doc], "cat.md": ["cat", doc, "--comments"],
                       "comments.json": ["comments", doc, "--all"], "info.json": ["info", doc]}.items():
        r = subprocess.run(["gdoc", *args, "--account", account, "--json"], capture_output=True, text=True)
        (folder / name).write_text(r.stdout or r.stderr)


def make(account, fx, task, surface):
    key = {"short": "short_template", "formatted": "formatted", "long": "long"}[task["fixture"]]
    doc = gdoc(account, "cp", fx[key]["id"], f"surface {task['id']} {surface}")["id"]
    comment = ""
    if task["fixture"] != "long":
        comment = gdoc(account, "comment", doc, COMMENT[0], "--quote", COMMENT[1]).get("id", "")
        gdoc(account, "suggest", doc, *SUGGESTION)
    for cmd in task.get("setup_extra", []):
        args = shlex.split(cmd.replace("{TASK_TAG}", f"{task['id']}-{surface}").replace("COMMENT_A", comment).replace("DOC", doc))
        gdoc(account, *(args[1:] if args[0] == "gdoc" else args))
    return doc


def main(side, surfaces, tasks_file=None, out=None):
    out = pathlib.Path(out) if out else SURFACE
    fx = json.loads((SURFACE / side / "fixtures.json").read_text())
    tasks = json.loads(pathlib.Path(tasks_file or SURFACE / "tasks.json").read_text())
    path = out / side / "copies.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    copies = json.loads(path.read_text()) if path.exists() else {}
    lock = threading.Lock()

    def one(task, surface):
        if copies.get(surface, {}).get(task["id"]):
            return
        try:
            doc = make(fx["account"], fx, task, surface)
            snapshot(fx["account"], doc, out / side / "base" / surface / task["id"])
        except Exception as e:
            print(f"{side} {surface} {task['id']}: {e}", file=sys.stderr)
            return
        with lock:
            copies.setdefault(surface, {})[task["id"]] = doc
            path.write_text(json.dumps(copies, indent=1))
        print(side, surface, task["id"], flush=True)

    with cf.ThreadPoolExecutor(3) as pool:
        list(pool.map(lambda a: one(*a), [(t, s) for s in surfaces for t in tasks]))
    print(f"{sum(len(v) for v in copies.values())} copies -> {path}")


if __name__ == "__main__":
    argv = sys.argv[1:]
    opt = lambda k: argv[argv.index(k) + 1] if k in argv else None
    pos = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or not argv[i - 1].startswith("--"))]
    main(pos[0], pos[1:] or ["cli", "web"], opt("--tasks"), opt("--out"))
