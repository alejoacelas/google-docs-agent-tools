"""Build matrix.json from the task catalog, grading results and latency timings.

Inputs live in the ignored .supervise/tool-matrix/ directory:
  tasks.json            task catalog
  grades.json           graded results (partial while grading runs)
  latency/timings.json  timed single commands (optional)
  latency/definitions.json  per-session definition cost (optional)
  regrades/*.json       targeted regrades after a change outside the tools' code (for example a
                        new Google API feature); each result replaces that tool's grade for the task
Route command names are normalized with the aliases in latency/spec-<tool>.json,
so graded routes and timed commands use the same names.
"""
import json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

ROOT = pathlib.Path(__file__).resolve().parents[3]
TM = ROOT / ".supervise/tool-matrix"

from taxonomy import TOOLS, PURPOSES, ITEMS, APPLICABLE, VARIATIONS


def assemble(tools, grades, latency, definitions):
    """The page's data: catalog, results for the given tools, and timings."""
    tasks = json.loads((TM / "tasks.json").read_text())
    aliases = {}
    for t in TOOLS:
        spec = pathlib.Path(__file__).parent / f"latency/spec-{t['id']}.json"
        if spec.exists():
            aliases[t["id"]] = json.loads(spec.read_text()).get("aliases", {})
    for g in grades:
        names = aliases.get(g["tool"].split("@")[0], {})  # a pull-request column ("gdoc@pr72") uses its tool's names
        for step in g.get("route", []):
            step["command"] = names.get(step["command"], step["command"])
    return {
        "schema": 1,
        "mock": False,
        "partial": len(grades) < len(tools) * len(tasks),
        "tools": tools,
        "purposes": [{"id": a, "label": b, "outcome": c} for a, b, c in PURPOSES],
        "items": [{"id": a, "label": b, "group": c} for a, b, c in ITEMS],
        "applicable": APPLICABLE,
        "variations": [{"id": a, "label": b, "group": c} for a, b, c in VARIATIONS],
        "tasks": [{k: t[k] for k in ("id", "sentence", "purpose", "item", "tags", "context")} for t in tasks],
        "results": grades,
        "latency": latency,
        "definitions": definitions,
    }


def regraded(grades):
    """Apply regrades/*.json over the pipeline's grades, in file-name order."""
    by = {(g["tool"], g["task"]): g for g in grades}
    for f in sorted((TM / "regrades").glob("*.json")):
        for x in json.loads(f.read_text()):
            if (x["tool"], x["task"]) in by:
                by[(x["tool"], x["task"])] = {**x, "stage": "regraded"}
    return list(by.values())


def main(out):
    load = lambda p: json.loads(p.read_text()) if p.exists() else []
    grades = regraded(load(TM / "grades.json"))
    data = assemble(TOOLS, grades, load(TM / "latency/timings.json"), load(TM / "latency/definitions.json"))
    pathlib.Path(out).write_text(json.dumps(data, indent=1, ensure_ascii=False))
    print(f"{len(data['tasks'])} tasks, {len(grades)} results, {len(data['latency'])} timings -> {out}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[1] / "matrix.json")
