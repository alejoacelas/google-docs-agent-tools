"""Rebuild matrix.json from whatever the grading run has finished so far.

    python3 preview.py              rebuild once
    python3 preview.py --watch 3    rebuild every 3 minutes until stopped
    python3 preview.py --run pr72   same for a pull-request run; open /planning/tool-matrix/?data=matrix-pr72.json

Serve the repository root (python3 -m http.server 8768 --bind 127.0.0.1) and open
/planning/tool-matrix/. While results are partial, the page reloads its data every
two minutes, so a watching preview keeps the open page current.
"""
import argparse, pathlib, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import build, collect, pr

ap = argparse.ArgumentParser()
ap.add_argument("--journal", type=pathlib.Path)
ap.add_argument("--watch", type=float, metavar="MINUTES")
ap.add_argument("--run", metavar="NAME")
a = ap.parse_args()
while True:
    print(time.strftime("%H:%M"), end=" ")
    if a.run:
        pr.collect_run(a.run, a.journal)
        pr.build_run(a.run)
    else:
        collect.grades(a.journal or collect.find_journal("grade:"))
        build.main(build.ROOT / "planning/tool-matrix/matrix.json")
    if not a.watch:
        break
    time.sleep(a.watch * 60)
