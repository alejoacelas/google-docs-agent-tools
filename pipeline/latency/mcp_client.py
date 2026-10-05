"""Minimal stdio MCP client for timing single Workspace MCP tool calls."""
import json, subprocess, time, os, select

class MCP:
    def __init__(self, cmd):
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=open(__import__('pathlib').Path(__file__).resolve().parents[4] / '.supervise/tool-matrix/latency/mcp-server.stderr', 'a'), text=True, bufsize=1)
        self.n = 0
        t = time.perf_counter()
        self.rpc('initialize', {'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'latency', 'version': '0'}})
        self.send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        self.startup_s = time.perf_counter() - t
    def send(self, m):
        self.p.stdin.write(json.dumps(m) + '\n'); self.p.stdin.flush()
    def rpc(self, method, params, timeout=180):
        self.n += 1; i = self.n
        self.send({'jsonrpc': '2.0', 'id': i, 'method': method, 'params': params})
        end = time.time() + timeout
        while time.time() < end:
            r, _, _ = select.select([self.p.stdout], [], [], 1)
            if not r: continue
            line = self.p.stdout.readline()
            if not line: raise RuntimeError('server exited')
            try: m = json.loads(line)
            except ValueError: continue
            if m.get('id') == i: return m
        raise TimeoutError(method)
    def call(self, name, arguments):
        t = time.perf_counter()
        m = self.rpc('tools/call', {'name': name, 'arguments': arguments})
        dt = time.perf_counter() - t
        res = m.get('result') or {}
        text = ''.join(c.get('text', '') for c in res.get('content', []) if isinstance(c, dict))
        return dt, (not res.get('isError') and 'error' not in m), text or json.dumps(m.get('error'))
    def close(self):
        self.p.terminate()

if __name__ == '__main__':
    m = MCP(['workspace-mcp', '--single-user', '--tools', 'docs', 'drive'])
    print('startup', round(m.startup_s, 2))
    tools = m.rpc('tools/list', {})['result']['tools']
    print(len(tools), sorted(t['name'] for t in tools)[:80])
    m.close()
