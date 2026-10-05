"""Time single commands live and count the tokens they return.

    uv run --with tiktoken python run.py [--dry] [--tool gdoc] [--only cat edit] [--runs 5]

Reads spec-<tool>.json (what to run) and .supervise/tool-matrix/latency/fixtures.json
(which synthetic documents to run it on). Writes, under .supervise/tool-matrix/latency/:
  samples-<tool>.jsonl   every timed call: command, fixture, ms, tokens, ok, error
  timings.json           per command and fixture: median/min/max ms, median tokens
  definitions.json       per-session definition cost in tokens

--dry runs every spec entry once and prints failures without touching timings.json.
Samples are saved as each call finishes, and timings.json is rewritten after every
command, so an interrupted run keeps its work; --resume skips commands that already
have the requested number of successful runs on every fixture.
CLI timings include process start-up, which an agent pays on every call. MCP
timings are per tools/call on a running server; start-up is recorded separately.
"""
import argparse, json, pathlib, re, statistics, subprocess, sys, tempfile, time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / ".supervise/tool-matrix/latency"
sys.path.insert(0, str(HERE))
from mcp_client import MCP

import tiktoken

# Docs allows 60 write requests per minute per user; one call can send several,
# so calls start at least this many seconds apart (the wait is not timed).
GAP = 1.2

ENC = tiktoken.get_encoding("cl100k_base")
tokens = lambda s: len(ENC.encode(s or "", disallowed_special=()))


def fill(x, values):
    """Substitute {placeholders} recursively; a whole-string numeric placeholder becomes a number."""
    if isinstance(x, str):
        m = re.fullmatch(r"\{(\w+)\}", x)
        if m and m.group(1) in values and re.fullmatch(r"-?\d+", str(values[m.group(1)])):
            return int(values[m.group(1)])
        return re.sub(r"\{(file:)?([\w.]+)\}", lambda m: str(values.get((m.group(1) or "") + m.group(2), m.group(0))), x)
    if isinstance(x, list):
        return [fill(v, values) for v in x]
    if isinstance(x, dict):
        return {k: fill(v, values) for k, v in x.items()}
    return x


class Runner:
    def __init__(self, tool):
        self.tool = tool
        self.last = 0.0
        self.mcp = None
        if tool == "taylor":
            self.mcp = MCP(["workspace-mcp", "--single-user", "--tools", "docs", "drive"])

    def call(self, step, stdin=None, expect=(0,)):
        """Run one call; space calls out and retry Google rate-limit errors, which are not timed."""
        for attempt in range(4):
            wait = self.last + GAP - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            ms, ok, text = self._call(step, stdin, expect)
            self.last = time.monotonic()
            if ok or not re.search(r"429|rateLimitExceeded|RATE_LIMIT", text or ""):
                return ms, ok, text
            time.sleep(30 * (attempt + 1))
        return ms, ok, text

    def _call(self, step, stdin=None, expect=(0,)):
        """Run one CLI argv (list) or MCP call (dict). Returns ms, ok, output text."""
        if isinstance(step, dict):
            dt, ok, text = self.mcp.call(step["tool"], step.get("arguments", {}))
            return dt * 1000, ok, text
        t = time.perf_counter()
        r = subprocess.run(step, input=stdin, capture_output=True, text=True, timeout=300)
        dt = (time.perf_counter() - t) * 1000
        ok = r.returncode in expect
        return dt, ok, r.stdout if ok else (r.stdout + r.stderr)

    def close(self):
        if self.mcp:
            self.mcp.close()


def values_for(fx, fixture, tool, run, files):
    doc = fx[f"short_{tool}"] if fixture == "short" else fx[fixture]
    tabs = doc.get("tabs", [{}, {}])
    return {
        "doc": doc["id"], "account": fx["account"], "folder": fx["folder"], "folder2": fx["folder2"],
        "tab_id": tabs[1].get("id", "") if len(tabs) > 1 else "", "tab_title": "Appendix",
        "child_tab_id": doc.get("child_tab", ""), "comment_id": doc.get("comment") or "",
        "run": run, **files,
    }


def capture(rules, text, values):
    for name, rx in (rules or {}).items():
        m = re.search(rx, text or "", re.S)
        if m:
            values[name] = m.group(1)


def run_entry(runner, entry, fx, runs, samples, log, save):
    tool = runner.tool
    step_key = "call" if tool == "taylor" else "argv"
    for fixture in entry.get("fixtures", ["short"]):
        for run in range(1, runs + 1):
            with tempfile.TemporaryDirectory() as tmp:
                files = {}
                for name, content in (entry.get("files") or {}).items():
                    p = pathlib.Path(tmp) / name
                    p.write_text(content)
                    files["file:" + name] = str(p)
                v = values_for(fx, fixture, tool, run, files)
                for pre in entry.get("pre", []):
                    _, ok, text = runner.call(fill(pre, v))
                    capture(entry.get("pre_capture"), text, v)
                    if not ok:
                        log(f"{tool} {entry['command']} pre failed: {text[:300]}")
                ms, ok, text = runner.call(fill(entry[step_key], v), fill(entry.get("stdin"), v), tuple(entry.get("expect_exit", [0])))
                save({"tool": tool, "command": entry["command"], "fixture": fixture, "run": run,
                      "ms": round(ms, 1), "tokens": tokens(text) if ok else None, "ok": ok,
                      "error": None if ok else text[:500]})
                if not ok:
                    log(f"{tool} {entry['command']} [{fixture}] failed: {text[:300]}")
                if entry.get("undo"):
                    capture(entry.get("capture"), text, v)
                    ms, uok, utext = runner.call(fill(entry["undo"], v))
                    save({"tool": tool, "command": entry.get("undo_command", entry["command"]),
                          "fixture": fixture, "run": run, "ms": round(ms, 1),
                          "tokens": tokens(utext) if uok else None, "ok": uok,
                          "error": None if uok else utext[:500], "undo": True})
                    if not uok:
                        log(f"{tool} {entry['command']} UNDO failed — document may not be back to its start: {utext[:300]}")


def summarize(samples):
    groups = {}
    for s in samples:
        groups.setdefault((s["tool"], s["command"], s["fixture"]), []).append(s)
    out = []
    for (tool, cmd, fixture), ss in sorted(groups.items()):
        good = [s for s in ss if s["ok"]]
        row = {"tool": tool, "command": cmd, "fixture": fixture, "runs": len(good), "failed": len(ss) - len(good)}
        if good:
            ms = [s["ms"] for s in good]
            row.update(status="measured", median_ms=round(statistics.median(ms)), min_ms=round(min(ms)),
                       max_ms=round(max(ms)), tokens_median=round(statistics.median(s["tokens"] for s in good)))
        else:
            row.update(status="failed", error=ss[0]["error"])
        out.append(row)
    return out


def definitions(tool, spec, runner):
    """Tokens an agent loads before its first call."""
    if tool == "taylor":
        listed = runner.mcp.rpc("tools/list", {})["result"]["tools"]
        return {"tool": tool, "tokens": tokens(json.dumps(listed)), "source": f"tools/list, {len(listed)} docs and drive tools"}
    cmds = sorted({e["command"] for e in spec["commands"]})
    text = subprocess.run([tool, "--help"], capture_output=True, text=True).stdout
    for c in cmds:
        text += subprocess.run([tool, *c.split(), "--help"], capture_output=True, text=True).stdout
    return {"tool": tool, "tokens": tokens(text), "source": f"--help for the tool and its {len(cmds)} timed commands"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--tool", nargs="*", default=["gdoc", "taylor", "gog"])
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--runs", type=int, default=5)
    a = ap.parse_args()
    fx = json.loads((OUT / "fixtures.json").read_text())
    logf = (OUT / ("dry.log" if a.dry else "run.log")).open("a", buffering=1)

    def log(msg):
        print(msg, flush=True)
        logf.write(time.strftime("%H:%M:%S ") + msg + "\n")

    timings_path, defs_path = OUT / "timings.json", OUT / "definitions.json"
    for tool in a.tool:
        spec = json.loads((HERE / f"spec-{tool}.json").read_text())
        order = {"read": 0, "lookup": 1, "drive": 2, "create": 3, "pair": 4}
        entries = sorted((e for e in spec["commands"] if not a.only or e["command"] in a.only),
                         key=lambda e: order.get(e["kind"], 5))
        sample_path = OUT / f"samples-{tool}.jsonl"
        load = lambda: [json.loads(l) for l in sample_path.read_text().splitlines()] if sample_path.exists() else []
        if a.resume:
            have = {}
            for s_ in load():
                if not s_.get("dry") and s_["ok"] and not s_.get("undo"):
                    have[(s_["command"], s_["fixture"])] = have.get((s_["command"], s_["fixture"]), 0) + 1
            before = len(entries)
            entries = [e for e in entries if any(have.get((e["command"], f), 0) < a.runs for f in e.get("fixtures", ["short"]))]
            log(f"{tool}: resuming, {before - len(entries)} commands already complete, {len(entries)} to run")
        out = sample_path.open("a", buffering=1)
        session = []

        def save(sample):
            sample = {**sample, "dry": a.dry}
            out.write(json.dumps(sample) + "\n")
            session.append(sample)

        def write_timings():
            # Summaries use every non-dry sample on file, so resumed runs add up.
            new = summarize([s_ for s_ in load() if not s_.get("dry")])
            old = json.loads(timings_path.read_text()) if timings_path.exists() else []
            timings_path.write_text(json.dumps([r for r in old if r["tool"] != tool] + new, indent=1))

        runner = Runner(tool)
        try:
            if runner.mcp:
                log(f"taylor server start-up {runner.mcp.startup_s:.2f}s")
            for e in entries:
                if a.dry:
                    e = {**e, "fixtures": e.get("fixtures", ["short"])[:1]}
                run_entry(runner, e, fx, 1 if a.dry else a.runs, session, log, save)
                log(f"{tool} {e['command']} done")
                if not a.dry:
                    write_timings()
            if not a.dry:
                defs = json.loads(defs_path.read_text()) if defs_path.exists() else []
                defs_path.write_text(json.dumps([d for d in defs if d["tool"] != tool] + [definitions(tool, spec, runner)], indent=1))
        finally:
            runner.close()
            out.close()
        bad = [s_ for s_ in session if not s_["ok"]]
        log(f"{tool}: {len(session) - len(bad)} ok, {len(bad)} failed of {len(session)} calls")


if __name__ == "__main__":
    main()
