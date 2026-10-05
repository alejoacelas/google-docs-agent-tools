"""Print the Workflow `args` JSON for one pipeline stage: catalog, surfaces or grade.

    python3 args.py catalog | surfaces [TOOL ...] | grade [TOOL ...]
"""
import json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from taxonomy import PURPOSES, ITEMS, APPLICABLE, VARIATIONS, ITEM_HINTS

ROOT = HERE.parents[2]
SOURCE = ROOT / ".supervise/source"
TM = ROOT / ".supervise/tool-matrix"


def tools(ids):
    all_tools = json.loads((HERE / "tools.json").read_text())
    return [t for t in all_tools if not ids or t["id"] in ids]


def blob(t, sha=None, repo=None):
    return f"{repo or t['repo']}/blob/{sha or t['sha']}/"


def rubric(t, dir=None, sha=None, url=None, inventory=None):
    """The grading rubric for one tool, shared by the full run and pull-request runs."""
    return (HERE / "grading/rubric.md").read_text().format(
        name=t["grade_name"], version=t["version"], sha=sha or t["sha"],
        dir=dir or SOURCE / t["checkout"], url=url or blob(t),
        inventory=inventory or f"Command inventory written from this source (read it first; verify anything you rely on against the code): {TM}/surface-{t['id']}.md",
        acceptance=ROOT / "planning/ACCEPTANCE.md", extra=t["extra"])


SCHEMA = json.loads((HERE / "grading/batch-schema.json").read_text())


def catalog():
    return {
        "purposes": [{"id": a, "label": b, "outcome": c} for a, b, c in PURPOSES],
        "items": [{"id": a, "label": b, "hint": ITEM_HINTS[a]} for a, b, _ in ITEMS],
        "applicable": APPLICABLE,
        "tags": [{"id": a, "label": b} for a, b, _ in VARIATIONS],
    }


def surfaces(ids):
    return [{"id": t["id"], "name": t["surface_name"], "version": t["version"], "sha": t["sha"],
             "dir": str(SOURCE / t["checkout"]), "url": blob(t), "notes": str(ROOT / t["notes"].split(" ")[0]) + t["notes"][len(t["notes"].split(" ")[0]):],
             "scope": t["scope"], "binary": t["binary"]} for t in tools(ids)]


def grade(ids):
    chunks = json.loads((TM / "chunks.json").read_text())
    return {
        "purposes": [c["purpose"] for c in chunks],
        "tools": [{"id": t["id"], "rubric": rubric(t)} for t in tools(ids)],
        "schema": SCHEMA,
    }


if __name__ == "__main__":
    stage, ids = sys.argv[1], sys.argv[2:]
    print(json.dumps({"catalog": lambda: catalog(), "surfaces": lambda: surfaces(ids), "grade": lambda: grade(ids)}[stage]()))
