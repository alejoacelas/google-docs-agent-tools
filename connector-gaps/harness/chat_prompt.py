"""Print the JS that sends RUN's prompt as a new Claude chat (run it in a claude.ai/new tab)."""
import json, pathlib, sys
HERE = pathlib.Path(__file__).parent
run = sys.argv[1]
r = json.loads((HERE.parents[1] / ".supervise/connector-gaps/runs-the test account.json").read_text())[run]
p = json.loads((HERE / "tasks.json").read_text())[r["task"]]["prompt"].replace("{doc}", f"[doc-link]
print("""const ed=document.querySelector('.tiptap.ProseMirror'); ed.focus();
const dt=new DataTransfer(); dt.setData('text/plain', %s);
ed.dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true}));
await new Promise(r=>setTimeout(r,800));
const send=[...document.querySelectorAll('button')].find(b=>/^send/i.test(b.getAttribute('aria-label')||''));
send.click(); await new Promise(r=>setTimeout(r,5000)); location.pathname""" % json.dumps(p))
