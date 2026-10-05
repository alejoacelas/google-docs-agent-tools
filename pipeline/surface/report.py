"""Build planning/tool-matrix/e2e.json from the graded end-to-end runs.

    python3 report.py

Reads tasks and grades from .supervise/tool-matrix/{surface,main}/ (grades/*.json, written by
graders following grader.md) and writes one data file for e2e.html: per configuration and task
the outcome, failed checks, damage, route, calls and seconds. Document IDs and links are removed.
"""
import collections, glob, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[4]
TM = ROOT / ".supervise/tool-matrix"
OUT = ROOT / "planning/tool-matrix/e2e.json"
ID = re.compile(r"\b1[A-Za-z0-9_-]{30,}\b|https://docs\.google\.com/\S+|AAAC[A-Za-z0-9_-]{6,}")

CONFIGS = [
    {"id": "claude-code", "suite": "main", "name": "Claude Code + Claude's Google connectors", "account": "Workspace account"},
    {"id": "codex", "suite": "main", "name": "Codex + OpenAI's Google Drive app", "account": "personal Gmail"},
    {"id": "claude-gog", "suite": "main", "name": "Claude Code + gog CLI", "account": "personal Gmail"},
    {"id": "claude-code", "suite": "surface", "name": "Claude Code (surface check)", "account": "Workspace account"},
    {"id": "cowork", "suite": "surface", "name": "Cowork on claude.ai", "account": "Workspace account"},
    {"id": "codex", "suite": "surface", "name": "Codex (surface check)", "account": "personal Gmail"},
    {"id": "chatgpt", "suite": "surface", "name": "ChatGPT on chatgpt.com", "account": "personal Gmail"},
]


def scrub(x):
    if isinstance(x, str):
        return ID.sub("[id]", x)
    if isinstance(x, list):
        return [scrub(v) for v in x]
    if isinstance(x, dict):
        return {k: scrub(v) for k, v in x.items()}
    return x


def grades(suite):
    rows = {}
    for f in sorted((TM / suite / "grades").glob("*.json")):  # later files (reruns) replace earlier ones
        for r in json.loads(f.read_text()):
            rows[(r["config"], r["task"])] = r
    return rows


def main():
    data = {"configs": [], "tasks": [], "results": []}
    for suite in ("main", "surface"):
        for t in json.loads((TM / suite / "tasks.json").read_text()):
            data["tasks"].append(scrub({"suite": suite, "id": t["id"], "category": t["category"], "mirrors": t.get("mirrors", []),
                                        "fixture": t["fixture"], "prompt": t["prompt"], "risk": t.get("risk", "")}))
        g = grades(suite)
        for c in [c for c in CONFIGS if c["suite"] == suite]:
            mine = [r for (cfg, _), r in g.items() if cfg == c["id"]]
            counts = collections.Counter(r["outcome"] for r in mine)
            data["configs"].append({**c, "graded": len(mine), "outcomes": dict(counts)})
            for r in mine:
                data["results"].append(scrub({
                    "suite": suite, "config": c["id"], "task": r["task"], "outcome": r["outcome"],
                    "failed": [ch["check"] for ch in r.get("checks", []) if ch.get("result") == "fail"],
                    "damage": r.get("damage") or "", "note": r.get("note") or "", "route": r.get("route", []),
                    "calls": r.get("calls"), "seconds": r.get("seconds")}))
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    for c in data["configs"]:
        print(f"{c['suite']:8} {c['name']:45} {c['graded']:3} {c['outcomes']}")
    print("->", OUT)


if __name__ == "__main__":
    main()
