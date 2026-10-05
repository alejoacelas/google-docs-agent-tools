"""Summarise Claude Code and Codex surface-check transcripts in the browser runs' format.

    python3 extract.py claude-code|codex|claude-gog [RUNS_DIR]   (default: surface/runs)

Reads runs/SURFACE/TASK.jsonl and .meta.json; writes runs/SURFACE/TASK.json with the
tool calls (name, input, result size, error), the final answer and the wall-clock time.
"""
import json, pathlib, sys

RUNS = pathlib.Path(__file__).resolve().parents[4] / ".supervise/tool-matrix/surface/runs"


def lines(path):
    for line in path.read_text(errors="ignore").splitlines():
        try:
            yield json.loads(line)
        except ValueError:
            continue


def claude_code(path):
    calls, results, answer, cost = {}, {}, "", None
    for e in lines(path):
        if e.get("type") == "assistant":
            for b in e["message"].get("content", []):
                if b.get("type") == "tool_use":
                    calls[b["id"]] = {"name": b["name"], "input": json.dumps(b["input"])[:2000]}
        elif e.get("type") == "user":
            for b in e["message"].get("content", []) if isinstance(e["message"].get("content"), list) else []:
                if b.get("type") == "tool_result":
                    text = json.dumps(b.get("content"))
                    results[b["tool_use_id"]] = {"result_chars": len(text), "is_error": bool(b.get("is_error")), "result_head": text[:300]}
        elif e.get("type") == "result":
            answer, cost = e.get("result", ""), e.get("total_cost_usd")
    return [{**c, **results.get(k, {})} for k, c in calls.items()], answer, {"cost_usd": cost}


def codex(path):
    calls, answer, usage = [], "", {}
    for e in lines(path):
        it = e.get("item", {})
        if e.get("type") == "item.completed" and it.get("type") == "mcp_tool_call":
            text = json.dumps(it.get("result"))
            calls.append({"name": f"{it.get('server')}.{it.get('tool')}", "input": json.dumps(it.get("arguments"))[:2000],
                          "result_chars": len(text), "is_error": bool(it.get("error")), "result_head": text[:300],
                          "error": it.get("error")})
        elif e.get("type") == "item.completed" and it.get("type") == "command_execution":
            calls.append({"name": "shell", "input": it.get("command", "")[:2000], "result_chars": len(it.get("aggregated_output") or ""),
                          "is_error": it.get("exit_code") not in (0, None), "result_head": (it.get("aggregated_output") or "")[:300]})
        elif e.get("type") == "item.completed" and it.get("type") == "agent_message":
            answer = it.get("text", "")
        elif e.get("type") == "turn.completed":
            usage = e.get("usage", {})
    return calls, answer, {"usage": usage}


def main(surface, runs=RUNS):
    parse = {"claude-code": claude_code, "claude-gog": claude_code, "codex": codex}[surface]
    for meta in sorted((runs / surface).glob("*.meta.json")):
        m = json.loads(meta.read_text())
        calls, answer, extra = parse(meta.with_name(f"{m['task']}.jsonl"))
        out = {"id": m["task"], "surface": surface, "doc": m["doc"], "seconds": m["seconds"], "exit": m["exit"],
               "tool_calls": calls, "final_answer": answer, **extra}
        meta.with_name(f"{m['task']}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(surface, len(list((runs / surface).glob("*.meta.json"))), "summaries")


if __name__ == "__main__":
    main(sys.argv[1], pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else RUNS)
