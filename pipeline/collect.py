"""Turn workflow journals into the pipeline's data files in .supervise/tool-matrix/.

    python3 collect.py tasks  [--journal PATH]   catalog run  -> tasks.json, chunks.json, chunks/
    python3 collect.py grades [--journal PATH]   grading run  -> grades.json

Without --journal, the newest Claude Code workflow journal containing that stage's
agents is used. A journal keeps one line per finished agent, so a run that is still
going (or was interrupted) yields partial results.
"""
import argparse, collections, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[3]
TM = ROOT / ".supervise/tool-matrix"
JOURNALS = pathlib.Path.home() / ".claude/projects"
CHUNK = 30


def find_journal(prefix):
    found = []
    for j in JOURNALS.glob("*/*/subagents/workflows/*/journal.jsonl"):
        head = j.read_text(errors="ignore")[:200000]
        if f'"label":"{prefix}' in head.replace(" ", ""):
            found.append(j)
    if not found:
        raise SystemExit(f"No workflow journal with {prefix!r} agents under {JOURNALS}")
    return max(found, key=lambda p: p.stat().st_mtime)


def read(journal):
    rows = [json.loads(line) for line in journal.read_text().splitlines() if line.strip()]
    labels = {r["agentId"]: r.get("label", "") for r in rows if r.get("type") == "started"}
    started = collections.Counter(l.split(":")[0] for l in labels.values())
    results = [(labels.get(r["agentId"], ""), r["result"]) for r in rows if r.get("type") == "result" and r.get("result")]
    return started, results


def tasks(journal):
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from taxonomy import PURPOSES, APPLICABLE
    _, results = read(journal)
    critic = {label.split(":")[1]: r for label, r in results if label.startswith("critic:")}
    norm = lambda s: re.sub(r"\W+", " ", s.lower()).strip()
    out, seen, count = [], set(), collections.Counter()
    for pid, *_ in PURPOSES:
        if pid not in critic:
            print(f"missing critic result for {pid}")
            continue
        for t in critic[pid]["tasks"]:
            key = (pid, norm(t["sentence"]))
            if t["purpose"] != pid or t["item"] not in APPLICABLE[pid] or key in seen:
                continue
            seen.add(key)
            count[(pid, t["item"])] += 1
            out.append({**t, "id": f"{pid}.{t['item']}.{count[(pid, t['item'])]}"})
    (TM / "tasks.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    chunks = []
    for pid, *_ in PURPOSES:
        ids = [t["id"] for t in out if t["purpose"] == pid]
        chunks += [{"purpose": pid, "ids": ids[i:i + CHUNK]} for i in range(0, len(ids), CHUNK)]
    (TM / "chunks.json").write_text(json.dumps(chunks))
    (TM / "chunks").mkdir(exist_ok=True)
    by_id = {t["id"]: t for t in out}
    for i, c in enumerate(chunks):
        rows = [{k: by_id[x][k] for k in ("id", "item", "purpose", "sentence", "tags")} for x in c["ids"]]
        (TM / f"chunks/chunk-{i:02d}.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    print(f"{len(out)} tasks in {len(chunks)} chunks from {journal}")


def grades(journal, quiet=False):
    started, results = read(journal)
    best = {}
    done = collections.Counter()
    for label, r in results:
        stage, tool, _ = label.split(":")
        done[stage] += 1
        for x in r["results"]:
            key = (tool, x["task"])
            if stage == "verify" or key not in best:
                best[key] = {**x, "tool": tool, "stage": "verified" if stage == "verify" else "graded"}
    (TM / "grades.json").write_text(json.dumps(list(best.values()), indent=1, ensure_ascii=False))
    if not quiet:
        per = collections.Counter((g["tool"], g["stage"]) for g in best.values())
        print(f"grading batches done {done['grade']}/{started['grade']} started, "
              f"verification done {done['verify']}/{started['verify']} started; "
              + ", ".join(f"{t} {s} {n}" for (t, s), n in sorted(per.items())))
    return best


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["tasks", "grades"])
    ap.add_argument("--journal", type=pathlib.Path)
    a = ap.parse_args()
    j = a.journal or find_journal("critic:" if a.what == "tasks" else "grade:")
    (tasks if a.what == "tasks" else grades)(j)
