"""Trap tests: does Cowork fall into the native Docs connector's traps on ordinary requests?

Each run gets a freshly built synthetic document in the the organization account (unshared folder),
a snapshot before and after the Cowork task, and a diff of everything that changed.
Run with gdoc's Python (first line of `which gdoc`). IDs and snapshots stay in
.supervise/trap-tests/.

    python harness.py folder                 create the test folder
    python harness.py build RUN CASE         build RUN's document, snapshot "before"
    python harness.py snap RUN               snapshot "after"
    python harness.py diff RUN               print what changed
    python harness.py inject RUN [N SEC]     act as a collaborator: N edits, SEC apart
"""
import difflib, json, pathlib, subprocess, sys, time

ACCOUNT = "[email]"
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / ".supervise/trap-tests"
RUNS = OUT / "runs.json"
CASES = json.loads((pathlib.Path(__file__).parent / "cases.json").read_text())

BASE = """# Onboarding pilot — Q4 plan

Owner: Sam Rivera. Reviewers: Ana, Ben.

## Summary

Status: On track. The onboarding pilot runs with four **[pilot teams](https://example.com/pilot)** from October to December. Each team will recieve a starter kit and a named contact.

We expect most teams to finish onboarding within two weeks.

Early findings will go in the Results section.

## Timeline

- Kickoff: Monday 6 October
- Launch review: Friday 7 November
- Retrospective: Friday 12 December

Weekly check-ins with pilot teams happen every Friday afternoon.

## Budget

| Line | Amount | Notes |
| --- | --- | --- |
| Starter kits | $4,000 | Shipped by the vendor |
| Contractor time | $12,500 | Two contractors |

## Milestones

| Milestone | Due | Status |
| --- | --- | --- |
| Kits shipped | 20 October | Not started |
| All pilot teams onboarded | 3 November | Not started |
| Launch review | 7 November | Not started |

## Risks

- The vendor may miss the kit delivery date.
- Two pilot teams share a manager, which could slow approvals.

## Results

Results will be added after the launch review.

## Next steps

- Confirm kit contents with the vendor
- Schedule the launch review
- Draft the retrospective template
"""


def gdoc(*args):
    r = subprocess.run(["gdoc", *args, "--account", ACCOUNT, "--json"], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"gdoc {args[0]} failed: {r.stderr.strip()} {r.stdout.strip()}")
    return json.loads(r.stdout) if r.stdout.strip() else {}


def svc():
    import gdoc.util
    from gdoc.api.docs import get_docs_service
    gdoc.util._active_account.set(ACCOUNT)
    return get_docs_service()


def import_markdown(title, md, folder):
    """Create the document with Google's own Markdown import, as a person uploading a .md file would."""
    import io, gdoc.util
    from gdoc.api.drive import get_drive_service
    from googleapiclient.http import MediaIoBaseUpload
    gdoc.util._active_account.set(ACCOUNT)
    media = MediaIoBaseUpload(io.BytesIO(md.encode()), mimetype="text/markdown")
    f = get_drive_service().files().create(body={"name": title, "parents": [folder], "mimeType": "application/vnd.google-apps.document"},
                                           media_body=media, fields="id").execute()
    return f["id"]


def runs():
    return json.loads(RUNS.read_text()) if RUNS.exists() else {}


def save_runs(r):
    RUNS.write_text(json.dumps(r, indent=1))


def content(s, doc):
    d = s.documents().get(documentId=doc, includeTabsContent=True).execute()
    return d, d["tabs"][0]["documentTab"]["body"]["content"]


def u16(t):
    return len(t.encode("utf-16-le")) // 2


def find(cont, text):
    for el in cont:
        els = el.get("paragraph", {}).get("elements", [])
        joined = "".join(pe.get("textRun", {}).get("content", "") for pe in els)
        i = joined.find(text)
        if i >= 0:
            return els[0]["startIndex"] + u16(joined[:i])
    raise KeyError(text)


def para_of(cont, text):
    for el in cont:
        p = el.get("paragraph")
        if p and text in "".join(pe.get("textRun", {}).get("content", "") for pe in p["elements"]):
            return el
    raise KeyError(text)


def batch(s, doc, reqs):
    return s.documents().batchUpdate(documentId=doc, body={"requests": reqs}).execute()


def enrich(s, doc):
    """Parts Markdown can't express: header, empty line above Results, heading link, fixed widths."""
    d, cont = content(s, doc)
    tab = d["tabs"][0]["tabProperties"]["tabId"]
    batch(s, doc, [{"createHeader": {"type": "DEFAULT"}}])
    d, cont = content(s, doc)
    header = next(iter(d["tabs"][0]["documentTab"]["headers"]))
    batch(s, doc, [{"insertText": {"location": {"segmentId": header, "index": 0, "tabId": tab}, "text": "Onboarding pilot · internal"}}])
    # Empty paragraph above the Results heading, typed the way a person would leave one.
    at = para_of(cont, "Results will be added")["startIndex"]
    heading = next(el for el in cont if el.get("paragraph", {}).get("paragraphStyle", {}).get("namedStyleType", "").startswith("HEADING")
                   and "Results" in "".join(pe.get("textRun", {}).get("content", "") for pe in el["paragraph"]["elements"]))
    batch(s, doc, [{"insertText": {"location": {"index": heading["startIndex"], "tabId": tab}, "text": "\n"}},
                   {"updateParagraphStyle": {"range": {"startIndex": heading["startIndex"], "endIndex": heading["startIndex"] + 1, "tabId": tab},
                                             "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"}, "fields": "namedStyleType"}}])
    d, cont = content(s, doc)
    heading = next(el for el in cont if el.get("paragraph", {}).get("paragraphStyle", {}).get("namedStyleType") == "HEADING_2"
                   and "Results" in "".join(pe.get("textRun", {}).get("content", "") for pe in el["paragraph"]["elements"]))
    hid = heading["paragraph"]["paragraphStyle"]["headingId"]
    at = find(cont, "Results section")
    batch(s, doc, [{"updateTextStyle": {"range": {"startIndex": at, "endIndex": at + u16("Results section"), "tabId": tab},
                                        "textStyle": {"link": {"heading": {"id": hid, "tabId": tab}}}, "fields": "link"}}])
    # Fixed column widths on the Milestones table.
    d, cont = content(s, doc)
    table = [el for el in cont if "table" in el][1]
    batch(s, doc, [{"updateTableColumnProperties": {"tableStartLocation": {"index": table["startIndex"], "tabId": tab},
                                                    "columnIndices": [i], "fields": "width,widthType",
                                                    "tableColumnProperties": {"widthType": "FIXED_WIDTH", "width": {"magnitude": w, "unit": "PT"}}}}
                   for i, w in enumerate([180, 90, 110])])


def build(run, case):
    r = runs()
    folder = r["_folder"]
    if not run.endswith("#1"):  # re-runs get their own folder so they can't see each other's files
        folder = gdoc("mkdir", f"Run {run}", "--parent", folder)["id"]
    title = f"Onboarding pilot — Q4 plan ({run})"
    doc = import_markdown(title, BASE, folder)
    s = svc()
    enrich(s, doc)
    gdoc("comment", doc, "This feels vague. What counts as finishing onboarding?", "--quote", "We expect most teams to finish onboarding within two weeks.")
    gdoc("comment", doc, "Does this include tax?", "--quote", "$12,500")
    gdoc("suggest", doc, "may miss the kit delivery date.", "may miss the kit delivery date if the vendor's warehouse move slips.")
    if case == "T01b":  # only "pilot" is linked in the check-ins line, so the match's first character differs from the rest
        d, cont = content(s, doc)
        at = find(cont, "with pilot teams") + u16("with ")
        batch(s, doc, [{"updateTextStyle": {"range": {"startIndex": at, "endIndex": at + u16("pilot"), "tabId": d["tabs"][0]["tabProperties"]["tabId"]},
                                            "textStyle": {"link": {"url": "https://example.com/pilot"}}, "fields": "link"}}])
    r[run] = {"case": case, "doc": doc, "folder": folder, "built": time.time()}
    save_runs(r)
    snap(run, "before")
    return doc


def raw(doc):
    import gdoc.util
    from gdoc.api.docs import _comments_view_get
    from gdoc.api.comments import list_comments
    gdoc.util._active_account.set(ACCOUNT)
    resp = _comments_view_get(doc)
    resp.raise_for_status()
    return {"doc": resp.json(), "comments": list_comments(doc, include_resolved=True)}


def snap(run, label):
    r = runs()
    doc = r[run]["doc"]
    data = raw(doc)
    (OUT / "snaps").mkdir(parents=True, exist_ok=True)
    (OUT / "snaps" / f"{run}-{label}.json").write_text(json.dumps(data))
    if label == "after" and r[run].get("copy"):
        (OUT / "snaps" / f"{run}-copy.json").write_text(json.dumps(raw(r[run]["copy"])))


# ---- rendering for diffs ----

def run_text(pe):
    if "textRun" in pe:
        t = pe["textRun"]
        st = t.get("textStyle", {})
        marks = "".join(k for k, f in (("B", "bold"), ("I", "italic"), ("U", "underline")) if st.get(f))
        link = st.get("link")
        if link:
            marks += "→" + (link.get("url") or ("#heading" if "heading" in link or "headingId" in link else "#other"))
        sug = "+S" if t.get("suggestedInsertionIds") else "-S" if t.get("suggestedDeletionIds") else ""
        txt = t["content"].replace("\n", "")
        return f"[{marks}{sug}]{txt}" if (marks or sug) else txt
    for k in ("footnoteReference", "inlineObjectElement", "person", "richLink", "pageBreak"):
        if k in pe:
            return f"<{k}>"
    return "<?>"


def lines(doc_json):
    tab = doc_json["tabs"][0]["documentTab"]
    out, headings = [], {}
    def para(el, prefix=""):
        p = el["paragraph"]
        ps = p.get("paragraphStyle", {})
        style = ps.get("namedStyleType", "?")
        hid = ps.get("headingId")
        if hid:
            headings[hid] = "".join(pe.get("textRun", {}).get("content", "") for pe in p["elements"]).strip()
        b = p.get("bullet")
        bullet = f" list={b['listId'][-4:]}/L{b.get('nestingLevel', 0)}" if b else ""
        out.append(f"{prefix}{style}{' id='+hid[-6:] if hid else ''}{bullet}: " + "".join(run_text(pe) for pe in p["elements"]))
    for el in tab["body"]["content"]:
        if "paragraph" in el:
            para(el)
        elif "table" in el:
            t = el["table"]
            widths = [(c.get("widthType", "?")[:5], c.get("width", {}).get("magnitude")) for c in t.get("tableStyle", {}).get("tableColumnProperties", [])]
            out.append(f"TABLE {t['rows']}x{t['columns']} widths={widths}")
            for ri, row in enumerate(t["tableRows"]):
                for ci, cell in enumerate(row["tableCells"]):
                    for cel in cell["content"]:
                        if "paragraph" in cel:
                            para(cel, f"  r{ri}c{ci} ")
    for hid, h in tab.get("headers", {}).items():
        out.append("HEADER: " + "".join(run_text(pe) for el in h["content"] for pe in el.get("paragraph", {}).get("elements", [])))
    ds = tab.get("documentStyle", {})
    out.append(f"HEADER IDS: default={ds.get('defaultHeaderId', '-')[-4:]} first={ds.get('firstPageHeaderId', '-')[-4:]} useFirst={ds.get('useFirstPageHeaderFooter')}")
    return out, headings


def anchors(data):
    tab = data["doc"]["tabs"][0]["documentTab"]
    text = []
    def walk(cont):
        for el in cont:
            if "paragraph" in el:
                for pe in el["paragraph"]["elements"]:
                    if "textRun" in pe:
                        text.append((pe["startIndex"], pe["textRun"]["content"]))
            elif "table" in el:
                for row in el["table"]["tableRows"]:
                    for cell in row["tableCells"]:
                        walk(cell["content"])
    walk(tab["body"]["content"])
    def slice_(a, b):
        out = ""
        for start, t in text:
            i = 0
            for ch in t:
                pos = start + i
                if a <= pos < b:
                    out += ch
                i += u16(ch)
        return out
    live = {aid: " | ".join(slice_(x.get("startIndex", 0), x.get("endIndex", 0)) for x in ca.get("ranges", []))
            for aid, ca in (tab.get("commentAnchors") or {}).items()}
    anchor_of = {c["commentId"]: c.get("anchorId") for c in data["doc"].get("comments", [])}
    res = []
    for c in data["comments"]:
        aid = anchor_of.get(c["id"])
        res.append(f"comment '{c.get('content', '')[:40]}' resolved={c.get('resolved', False)} replies={len(c.get('replies', []))} "
                   f"anchor_now={live.get(aid, 'DETACHED') if aid else 'unanchored'!r}")
    return sorted(res)


def suggestions(data):
    tab = data["doc"]["tabs"][0]["documentTab"]
    found = {}
    def walk(cont):
        for el in cont:
            if "paragraph" in el:
                for pe in el["paragraph"]["elements"]:
                    t = pe.get("textRun", {})
                    for k, sign in (("suggestedInsertionIds", "+"), ("suggestedDeletionIds", "-")):
                        for sid in t.get(k, []):
                            found.setdefault(sid, []).append(sign + t["content"])
                for sid in el["paragraph"].get("suggestedParagraphStyleChanges", {}):
                    found.setdefault(sid, []).append("~paragraph style")
            elif "table" in el:
                for row in el["table"]["tableRows"]:
                    for cell in row["tableCells"]:
                        walk(cell["content"])
    walk(tab["body"]["content"])
    return [f"{sid[-6:]}: {' '.join(v)}" for sid, v in sorted(found.items())]


def diff(run):
    b = json.loads((OUT / "snaps" / f"{run}-before.json").read_text())
    a = json.loads((OUT / "snaps" / f"{run}-after.json").read_text())
    out = [f"== {run} ({runs()[run]['case']}) revision changed: {b['doc'].get('revisionId') != a['doc'].get('revisionId')}"]
    (lb, hb), (la, ha) = lines(b["doc"]), lines(a["doc"])
    d = [l for l in difflib.unified_diff(lb, la, lineterm="", n=0) if not l.startswith(("---", "+++"))]
    out += ["-- body/header changes:"] + (d or ["(none)"])
    lost = [f"{k[-6:]} {v!r}" for k, v in hb.items() if k not in ha]
    if lost:
        out.append("-- heading IDs gone: " + ", ".join(lost))
    links = [l for l in la if "→#heading" in l]
    out.append(f"-- heading links now: {len(links)} (before {sum('→#heading' in l for l in lb)})")
    cb, cA = anchors(b), anchors(a)
    out += ["-- comments before:"] + cb + ["-- comments after:"] + cA
    sb, sa = suggestions(b), suggestions(a)
    out += ["-- suggestions before:"] + sb + ["-- suggestions after:"] + sa
    copy = OUT / "snaps" / f"{run}-copy.json"
    if copy.exists():
        c = json.loads(copy.read_text())
        out += ["-- copy: comments=%d suggestions=%d" % (len(c["comments"]), len(suggestions(c)))]
    return "\n".join(out)


def inject(run, n=10, sec=20):
    """A collaborator keeps adding reviewers to the line above the Summary, shifting every index after it."""
    s, doc = svc(), runs()[run]["doc"]
    names = ["Chen", "Dara", "Eli", "Fatima", "Goran", "Hana", "Ivo", "Jun", "Kemi", "Lior", "Mai", "Nils",
             "Omar", "Priya", "Quinn", "Rosa", "Sven", "Tara", "Uma", "Vik", "Wen", "Xavi", "Yara", "Zoe", "Ada"]
    for k in range(n):
        time.sleep(sec)
        d, cont = content(s, doc)
        at = find(cont, "Reviewers: ")
        p = para_of(cont, "Reviewers: ")
        end = p["endIndex"] - 2  # before the period and newline
        batch(s, doc, [{"insertText": {"location": {"index": end, "tabId": d["tabs"][0]["tabProperties"]["tabId"]}, "text": f", {names[k % len(names)]}"}}])
        print(f"inject {k + 1}/{n}", flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "base.md").write_text(BASE)
    if cmd == "folder":
        r = runs()
        r["_folder"] = r.get("_folder") or gdoc("mkdir", "Trap tests (synthetic)")["id"]
        save_runs(r)
        print("folder ok")
    elif cmd == "build" and sys.argv[3] == "T09":  # Markdown publish: the run starts from an empty folder
        r = runs()
        r[sys.argv[2]] = {"case": "T09", "doc": None, "folder": gdoc("mkdir", f"Run {sys.argv[2]}", "--parent", r["_folder"])["id"]}
        save_runs(r); print("prepared", sys.argv[2])
    elif cmd == "build":
        build(sys.argv[2], sys.argv[3]); print("built", sys.argv[2])
    elif cmd == "snap":
        snap(sys.argv[2], "after"); print("snapped", sys.argv[2])
    elif cmd == "diff":
        print(diff(sys.argv[2]))
    elif cmd == "inject":
        inject(sys.argv[2], *(int(x) for x in sys.argv[3:5]))
