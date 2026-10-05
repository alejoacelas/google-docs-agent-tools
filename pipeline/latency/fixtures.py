"""Create the synthetic documents used for latency and token timings.

All documents live in one new folder in the personal account and are retained.
FIXTURE_ACCOUNT, FIXTURE_DIR and FIXTURE_TOOLS (comma-separated) override the
account, the output folder under .supervise/tool-matrix/ and the tools that get
a short document.
Markdown content goes in with `gdoc new --file`; formatting Markdown cannot
express is added through gdoc's own authenticated Docs client. Writes:
.supervise/tool-matrix/latency/fixtures.json (IDs stay out of the repository).

    python3 fixtures.py
"""
import json, os, pathlib, re, subprocess, sys

ACCOUNT = os.environ.get("FIXTURE_ACCOUNT", "[email]")
ROOT = pathlib.Path(__file__).resolve().parents[4]
OUT = ROOT / ".supervise/tool-matrix" / os.environ.get("FIXTURE_DIR", "latency")
TOOLS = os.environ.get("FIXTURE_TOOLS", "gdoc,taylor,gog").split(",")
IMAGE = "https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png"

SECTION = """## Status {n}

The launch plan is on track and the alpha build ships to **pilot teams** this week. See the [project page](https://example.com/project) for details.

- Owners
  - Design review with the platform team
  - Budget sign-off
- Risks
  - Vendor delay

1. Confirm the schedule
2. Send the summary

| Item | Owner | Due |
| --- | --- | --- |
| Draft | Ana | Friday |
| Review | Ben | Monday |

"""
SHORT = "# Launch notes\n\nThis document tracks the launch. Last updated by the team.\n\n" + SECTION.format(n=1) + "## Notes\n\nOpen questions go here.\n"
LONG = "# Launch notes archive\n\nThis document collects weekly launch notes.\n\n" + "".join(SECTION.format(n=i) for i in range(1, 41))


def gdoc(*args):
    r = subprocess.run(["gdoc", *args, "--account", ACCOUNT, "--json"], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"gdoc {args[0]} failed: {r.stderr.strip()} {r.stdout.strip()}")
    return json.loads(r.stdout) if r.stdout.strip() else {}


def docs():
    import gdoc.util
    from gdoc.api.docs import get_docs_service
    gdoc.util._active_account.set(ACCOUNT)
    return get_docs_service()


def body(svc, doc):
    d = svc.documents().get(documentId=doc, includeTabsContent=True).execute()
    return d, d["tabs"][0]["documentTab"]["body"]["content"]


def find(content, text):
    """Index of text within a paragraph, even when it spans several formatting runs."""
    for el in content:
        elements = el.get("paragraph", {}).get("elements", [])
        joined = "".join(pe.get("textRun", {}).get("content", "") for pe in elements)
        i = joined.find(text)
        if i >= 0:
            return elements[0]["startIndex"] + len(joined[:i].encode("utf-16-le")) // 2
    raise KeyError(text)


def first_table(content):
    return next(el for el in content if "table" in el)


def update(svc, doc, requests):
    return svc.documents().batchUpdate(documentId=doc, body={"requests": requests}).execute()


def enrich(svc, doc):
    """Add the non-Markdown parts every short fixture shares."""
    d, content = body(svc, doc)
    tab = d["tabs"][0]["tabProperties"]["tabId"]
    table = first_table(content)
    update(svc, doc, [{"mergeTableCells": {"tableRange": {"tableCellLocation": {
        "tableStartLocation": {"index": table["startIndex"], "tabId": tab}, "rowIndex": 2, "columnIndex": 1},
        "rowSpan": 1, "columnSpan": 2}}}])
    _, content = body(svc, doc)
    at = find(content, "this week") + len("this week")
    update(svc, doc, [{"createFootnote": {"location": {"index": at, "tabId": tab}}}])
    d, _ = body(svc, doc)
    fn = next(iter(d["tabs"][0]["documentTab"]["footnotes"]))
    update(svc, doc, [
        {"insertText": {"location": {"segmentId": fn, "index": 1, "tabId": tab}, "text": "Pilot teams were chosen in March."}},
        {"createHeader": {"type": "DEFAULT"}},
    ])
    d, content = body(svc, doc)
    header = next(iter(d["tabs"][0]["documentTab"]["headers"]))
    update(svc, doc, [{"insertText": {"location": {"segmentId": header, "index": 0, "tabId": tab}, "text": "Launch notes · internal"}}])
    _, content = body(svc, doc)
    at = find(content, "Open questions")
    update(svc, doc, [{"insertInlineImage": {"location": {"index": at, "tabId": tab}, "uri": IMAGE,
                                              "objectSize": {"width": {"magnitude": 136, "unit": "PT"}}}}])
    update(svc, doc, [{"addDocumentTab": {"tabProperties": {"title": "Appendix"}}}])
    d, _ = body(svc, doc)
    parent = d["tabs"][1]["tabProperties"]["tabId"]
    update(svc, doc, [{"addDocumentTab": {"tabProperties": {"title": "Sources", "parentTabId": parent}}}])
    d, _ = body(svc, doc)
    for t in d["tabs"][1:]:
        stack = [t]
        while stack:
            x = stack.pop()
            update(svc, doc, [{"insertText": {"location": {"index": 1, "tabId": x["tabProperties"]["tabId"]},
                                               "text": f"{x['tabProperties']['title']}: supporting material for the launch.\n"}}])
            stack += x.get("childTabs", [])


def heavy_format(svc, doc):
    """Colors, highlights, fonts and many runs per paragraph; styled table cells."""
    d, content = body(svc, doc)
    tab = d["tabs"][0]["tabProperties"]["tabId"]
    reqs, palette = [], [(0.8, 0.1, 0.1), (0.1, 0.4, 0.8), (0.1, 0.6, 0.3)]
    fonts = ["Georgia", "Roboto Mono", "Arial"]
    for el in content:
        for pe in el.get("paragraph", {}).get("elements", []):
            run = pe.get("textRun")
            if not run:
                continue
            words = [(m.start(), m.end()) for m in re.finditer(r"\w+", run["content"])]
            for k, (a, b) in enumerate(words[::2]):
                s = pe["startIndex"] + len(run["content"][:a].encode("utf-16-le")) // 2
                e = pe["startIndex"] + len(run["content"][:b].encode("utf-16-le")) // 2
                r, g, bl = palette[k % 3]
                style = {"foregroundColor": {"color": {"rgbColor": {"red": r, "green": g, "blue": bl}}},
                         "weightedFontFamily": {"fontFamily": fonts[k % 3]}}
                fields = "foregroundColor,weightedFontFamily"
                if k % 4 == 0:
                    style["backgroundColor"] = {"color": {"rgbColor": {"red": 1, "green": 0.95, "blue": 0.6}}}
                    fields += ",backgroundColor"
                reqs.append({"updateTextStyle": {"range": {"startIndex": s, "endIndex": e, "tabId": tab},
                                                 "textStyle": style, "fields": fields}})
    table = first_table(content)
    reqs.append({"updateTableCellStyle": {"tableRange": {"tableCellLocation": {
        "tableStartLocation": {"index": table["startIndex"], "tabId": tab}, "rowIndex": 0, "columnIndex": 0},
        "rowSpan": 1, "columnSpan": 3},
        "tableCellStyle": {"backgroundColor": {"color": {"rgbColor": {"red": 0.85, "green": 0.9, "blue": 1}}}},
        "fields": "backgroundColor"}})
    for i in range(0, len(reqs), 200):
        update(svc, doc, reqs[i:i + 200])
    _, content = body(svc, doc)
    at = find(content, "Last updated by the team") + len("Last updated by the team")
    try:
        update(svc, doc, [{"insertPerson": {"location": {"index": at, "tabId": tab},
                                            "personProperties": {"email": ACCOUNT}}}])
    except Exception as e:  # chips are optional; record and continue
        print("person chip skipped:", e, file=sys.stderr)
    return len(reqs)


def build_short(title, folder, svc):
    src = OUT / "short.md"
    doc = gdoc("new", title, "--file", str(src), "--folder", folder)["id"]
    enrich(svc, doc)
    comment = gdoc("comment", doc, "Is the pilot date confirmed?", "--quote", "pilot teams")
    try:
        gdoc("suggest", doc, "Open questions go here.", "Open questions and decisions go here.")
        suggestion = True
    except RuntimeError as e:
        print("suggestion skipped:", e, file=sys.stderr)
        suggestion = False
    return {"id": doc, "comment": comment.get("id"), "suggestion": suggestion}


def existing(title):
    hits = gdoc("find", title)["files"]
    return next((f["id"] for f in hits if f["name"] == title), None)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "short.md").write_text(SHORT)
    (OUT / "long.md").write_text(LONG)
    path = OUT / "fixtures.json"
    fx = json.loads(path.read_text()) if path.exists() else {"account": ACCOUNT}
    save = lambda: path.write_text(json.dumps(fx, indent=2))
    fx["folder"] = fx.get("folder") or existing("tool-matrix latency fixtures") or gdoc("mkdir", "tool-matrix latency fixtures")["id"]
    fx["folder2"] = fx.get("folder2") or existing("tool-matrix latency moves") or gdoc("mkdir", "tool-matrix latency moves", "--parent", fx["folder"])["id"]
    save()
    svc = docs()
    for tool in TOOLS:
        key, title = f"short_{tool}", f"Latency fixture short ({tool})"
        if key not in fx:
            doc = existing(title)
            fx[key] = {"id": doc} if doc else build_short(title, fx["folder"], svc)
            save()
        print("short", tool, flush=True)
    if "formatted" not in fx:
        doc = existing("Latency fixture formatted")
        if doc:  # created and formatted by an interrupted run; only the chip may be missing
            fx["formatted"] = {"id": doc}
            _, content = body(svc, doc)
            at = find(content, "Last updated by the team") + len("Last updated by the team")
            try:
                update(svc, doc, [{"insertPerson": {"location": {"index": at}, "personProperties": {"email": ACCOUNT}}}])
            except Exception as e:
                print("person chip skipped:", e, file=sys.stderr)
        else:
            fx["formatted"] = build_short("Latency fixture formatted", fx["folder"], svc)
            fx["formatted"]["format_requests"] = heavy_format(svc, fx["formatted"]["id"])
        save()
    print("formatted", flush=True)
    if "long" not in fx:
        doc = existing("Latency fixture long")
        fx["long"] = {"id": doc or gdoc("new", "Latency fixture long", "--file", str(OUT / "long.md"), "--folder", fx["folder"])["id"]}
        save()
    print("long", flush=True)
    for key in [k for k in fx if k.startswith("short_")] + ["formatted"]:
        d, _ = body(svc, fx[key]["id"])
        fx[key]["tabs"] = [{"id": t["tabProperties"]["tabId"], "title": t["tabProperties"]["title"]} for t in d["tabs"]]
        fx[key]["child_tab"] = d["tabs"][1]["childTabs"][0]["tabProperties"]["tabId"]
        comments = gdoc("comments", fx[key]["id"]).get("comments", [])
        fx[key]["comment"] = comments[0]["id"] if comments else None
    save()
    print("wrote", path)


if __name__ == "__main__":
    main()
