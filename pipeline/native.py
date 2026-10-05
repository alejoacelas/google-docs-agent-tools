"""Grade closed, hosted Google connectors and compare them with gog.

    python3 native.py args  [CONNECTOR]                    Workflow args for workflows/grade.js
    python3 native.py build [CONNECTOR] [--journal PATH]   collect that connector's grades
    python3 native.py matrix                               -> planning/tool-matrix/matrix-connectors.json

CONNECTOR is "native" (Claude's Google-hosted Docs and Drive connectors, the default) or
"openai" (OpenAI's Google Drive app, used by ChatGPT and Codex). Their code is closed, so
graders read the tool definitions and a live probe log instead of source
(grading/rubric-native.md). Inputs and outputs stay in .supervise/tool-matrix/CONNECTOR/:
definitions.json, probes/<id>.json (written by probe workers), probes.json (merged here),
regrade-out-*.json (targeted regrades that replace earlier grades), grades.json.
"""
import json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import args as A, build, collect
from taxonomy import TOOLS

CONNECTORS = {
    "native": {
        "tool": {"id": "native", "name": "Claude's Google connectors", "interface": "MCP", "pin": "Docs + Drive, 2026-10-05"},
        "name": "Claude's Google connectors for Docs and Drive (Google-hosted MCP servers)",
        "passthrough": "`update_doc` passes a `documents.batchUpdate` request through unchanged, and `read_doc` returns the `documents.get` JSON, so a route is whatever sequence of Google requests the caller can build. Its description is cut off partway through `updateTextStyle`; assume the full public request list is accepted unless a probe shows a request being rejected.",
        "route_examples": '"read_doc", "update_doc", "copy_file", "search_files" …',
        "raw_tool": "update_doc",
    },
    "openai": {
        "tool": {"id": "openai", "name": "OpenAI's Google Drive app", "interface": "App", "pin": "ChatGPT/Codex, 2026-10-05"},
        "name": "OpenAI's Google Drive app (the connector ChatGPT and Codex use for Drive, Docs, Sheets and Slides)",
        "passthrough": "`batch_update_document` passes raw `documents.batchUpdate` requests; the read tools (`get_document`, `get_document_text`, `get_document_paragraph_range`, `get_document_tables`, `get_document_comments`, `find_document_text_range`) return OpenAI's own renderings, so check in the probe log what each one includes. Comments go through `bulk_update_file_comments` (Drive comments API) unless a probe shows the Docs comment requests work through `batch_update_document`.",
        "route_examples": '"get_document", "batch_update_document", "bulk_update_file_comments", "copy_file", "search" …',
        "raw_tool": "batch_update_document",
    },
}
COMPARE = ["gog"]
GROUP = 6  # chunks per grading agent


def probes(conn):
    d = A.TM / conn
    rows = [json.loads(p.read_text()) for p in sorted((d / "probes").glob("*.json"))]
    (d / "probes.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    return len(rows)


def workflow_args(conn):
    c, d = CONNECTORS[conn], A.TM / conn
    n = probes(conn)
    rubric = (HERE / "grading/rubric-native.md").read_text().format(
        name=c["name"], probes=f"{d / 'probes.json'} ({n} probes)", definitions=d / "definitions.json",
        passthrough=c["passthrough"], route_examples=c["route_examples"], raw_tool=c["raw_tool"],
        acceptance=A.ROOT / "planning/ACCEPTANCE.md",
        extra="Evidence entries need claim, ref and url; use the probe or definition reference as ref and an empty url.")
    chunks = json.loads((A.TM / "chunks.json").read_text())
    return {"purposes": [ch["purpose"] for ch in chunks], "tools": [{"id": conn, "rubric": rubric}],
            "schema": A.SCHEMA, "group": GROUP}


def collect_grades(conn, journal):
    d = A.TM / conn
    started, results = collect.read(journal or collect.find_journal(f"grade:{conn}"))
    grades = {}
    for label, r in results:
        stage, tool, _ = label.split(":")
        if tool == conn:
            for x in r["results"]:
                if stage == "verify" or x["task"] not in grades:
                    grades[x["task"]] = {**x, "tool": conn, "stage": "verified" if stage == "verify" else "graded"}
    for f in sorted(d.glob("regrade-out-*.json")):
        for x in json.loads(f.read_text())["results"]:
            if x["task"] in grades:
                grades[x["task"]] = {**x, "tool": conn, "stage": "regraded"}
    (d / "grades.json").write_text(json.dumps(list(grades.values()), indent=1, ensure_ascii=False))
    print(f"{conn}: {len(grades)} grades ({started['grade']} batches started)")


def matrix():
    load = lambda p: json.loads(p.read_text()) if p.exists() else []
    others = [g for g in build.regraded(load(A.TM / "grades.json")) if g["tool"] in COMPARE]
    have = [c for c in CONNECTORS if (A.TM / c / "grades.json").exists()]
    grades = others + [g for c in have for g in load(A.TM / c / "grades.json")]
    tools = [t for t in TOOLS if t["id"] in COMPARE] + [CONNECTORS[c]["tool"] for c in have]
    timings = [t for t in load(A.TM / "latency/timings.json") if t["tool"] in COMPARE]
    defs = [d for d in load(A.TM / "latency/definitions.json") if d["tool"] in COMPARE] + \
           [d for c in have for d in load(A.TM / c / "definition-cost.json")]
    data = build.assemble(tools, grades, timings, defs)
    out = HERE.parent / "matrix-connectors.json"
    out.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    print(f"{len(tools)} tools, {len(grades)} results -> {out}")


if __name__ == "__main__":
    cmd, rest = sys.argv[1], sys.argv[2:]
    conn = rest[0] if rest and not rest[0].startswith("--") else "native"
    journal = pathlib.Path(rest[rest.index("--journal") + 1]) if "--journal" in rest else None
    if cmd == "args":
        print(json.dumps(workflow_args(conn)))
    elif cmd == "build":
        collect_grades(conn, journal)
    else:
        matrix()
