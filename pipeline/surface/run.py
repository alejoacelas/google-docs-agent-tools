"""Run surface-check or main tasks through the scriptable surfaces.

    python3 run.py claude-code|codex|claude-gog [TASK ...] --workdir DIR [--jobs 3] [--tasks FILE --out DIR]

claude-code uses Claude's Google connectors (the organization fixtures), codex OpenAI's Google Drive app
(personal fixtures), and claude-gog Claude Code with only the gog CLI (personal fixtures).

Each task runs once, in a new session, on its own copy (SIDE/copies.json, surface "cli"),
with the task prompt verbatim. Runs are isolated to the hosted Google connector:
gdoc, gog and workspace-mcp are shadowed on PATH, Taylor's MCP server is off, and the
user's global instruction file (which recommends gdoc) is excluded or countered.
Transcripts go to .supervise/tool-matrix/surface/runs/SURFACE/TASK.jsonl with a .meta.json;
tasks with a finished meta file are skipped, so a rerun resumes.
"""
import argparse, concurrent.futures as cf, json, os, pathlib, subprocess, time

ROOT = pathlib.Path(__file__).resolve().parents[4]
SURFACE = ROOT / ".supervise/tool-matrix/surface"
BIN = SURFACE / "bin"
SIDE = {"claude-code": "claude", "codex": "openai", "claude-gog": "openai"}
COPIES = {"claude-code": "cli", "codex": "cli", "claude-gog": "gog"}
TIMEOUT = 15 * 60
CODEX_CONFIG = (pathlib.Path.home() / ".codex/config.toml").read_text() if (pathlib.Path.home() / ".codex/config.toml").exists() else ""


def path_env(surface="claude-code"):
    keep = [p for p in os.environ["PATH"].split(":") if ".local/bin" not in p]
    return f"{BIN if surface != 'claude-gog' else BIN.with_name('bin-gog')}:{':'.join(keep)}"


GOG_NOTE = "The gog CLI (gogcli) is installed and signed in as [email]; use it for Google Docs and Drive."


def command(surface, prompt):
    if surface == "claude-gog":
        return ["claude", "-p", "--dangerously-skip-permissions", "--disallowedTools",
                "mcp__workspace-google", "mcp__a local test server", "mcp__a local test server", "mcp__claude_ai_Google_Docs",
                "mcp__claude_ai_Google_Drive", "mcp__claude_ai_Gdoc_connector_v1",
                "--settings", json.dumps({"claudeMdExcludes": ["**/CLAUDE.md", "**/AGENTS.md"]}),
                "--append-system-prompt", GOG_NOTE, "--output-format", "stream-json", "--verbose", prompt]
    if surface == "claude-code":
        return ["claude", "-p", "--dangerously-skip-permissions", "--disallowedTools", "mcp__workspace-google", "mcp__a local test server", "mcp__a local test server",  # local servers Cowork lacks
                "--settings", json.dumps({"claudeMdExcludes": ["**/CLAUDE.md", "**/AGENTS.md"]}),
                "--output-format", "stream-json", "--verbose", prompt]
    path = path_env()
    return ["codex", "exec", "--json", "--dangerously-bypass-approvals-and-sandbox", "--skip-git-repo-check",
            # Replace the whole plugins table: the Drive app on; browser and computer use off, because
            # Codex otherwise opens the doc in Chrome (cua_repl) instead of using the Drive app.
            "-c", 'plugins={"google-drive@openai-curated-remote"={enabled=true},'
                  '"unified-computer-use@openai-bundled"={enabled=false},"browser@openai-bundled"={enabled=false},'
                  '"chrome@openai-bundled"={enabled=false},"computer-use@openai-bundled"={enabled=false}}',
            "-c", "apps.connector_5f3c8c41a1e54ad7a76272c89e2554fa.enabled=true",
            # Turn off local servers, but only those this machine defines (Codex rejects unknown ones).
            *[x for name in ("workspace-google", "computer-use", "node_repl") if f"[mcp_servers.{name}]" in CODEX_CONFIG
              for x in ("-c", f"mcp_servers.{name}.enabled=false")],
            "-c", f'shell_environment_policy.set.PATH="{path}"', "-c", 'shell_environment_policy.inherit="core"',
            "-c", 'developer_instructions="The gdoc CLI that the user instructions mention is not installed in this environment."',
            prompt]


def run(surface, task, doc, workdir, root=SURFACE):
    out = root / "runs" / surface
    out.mkdir(parents=True, exist_ok=True)
    meta = out / f"{task['id']}.meta.json"
    if meta.exists():
        return
    prompt = task["prompt"].replace("{DOC_URL}", f"[doc-link]
    prompt = prompt.replace("{TASK_TAG}", f"{task['id']}-{COPIES[surface]}")
    env = {**os.environ, "PATH": path_env(surface)}
    start = time.time()
    with open(out / f"{task['id']}.jsonl", "w") as log:
        try:
            p = subprocess.run(command(surface, prompt), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, cwd=workdir, env=env, timeout=TIMEOUT)
            code = p.returncode
        except subprocess.TimeoutExpired:
            code = "timeout"
    meta.write_text(json.dumps({"task": task["id"], "doc": doc, "prompt": prompt, "start": start,
                                "seconds": round(time.time() - start, 1), "exit": code}, indent=1))
    print(surface, task["id"], code, round(time.time() - start), "s", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("surface", choices=list(SIDE))
    ap.add_argument("tasks", nargs="*")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--tasks", dest="task_file", help="task file (default: the surface-check tasks.json)")
    ap.add_argument("--out", help="output root holding SIDE/copies.json and runs/ (default: the surface folder)")
    ap.add_argument("--workdir", required=True, help="an empty directory outside any repository, so no project instructions load")
    a = ap.parse_args()
    pathlib.Path(a.workdir).mkdir(parents=True, exist_ok=True)
    root = pathlib.Path(a.out) if a.out else SURFACE
    tasks = [t for t in json.loads(pathlib.Path(a.task_file or SURFACE / "tasks.json").read_text()) if not a.tasks or t["id"] in a.tasks]
    copies = json.loads((root / SIDE[a.surface] / "copies.json").read_text())[COPIES[a.surface]]
    with cf.ThreadPoolExecutor(a.jobs) as pool:
        list(pool.map(lambda t: run(a.surface, t, copies[t["id"]], a.workdir, root), [t for t in tasks if t["id"] in copies]))


if __name__ == "__main__":
    main()
