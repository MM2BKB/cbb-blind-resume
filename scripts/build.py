#!/usr/bin/env python3
"""Builds _site/index.html from template.html and the files in data/."""
import csv, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def p(*a): return os.path.join(ROOT, *a)

raw = open(p("data", "teams.csv")).read().strip("\n").replace("`", "")
lines = []
with open(p("data", "games.csv"), newline="") as f:
    for r in list(csv.reader(f))[1:]:
        if len(r) >= 6:
            lines.append(",".join(x.replace("`", "").replace(",", " ") if i < 2 else x for i, x in enumerate(r[1:6])))
meta = json.load(open(p("data", "meta.json"))) if os.path.exists(p("data", "meta.json")) else {}
html = open(p("template.html")).read()
html = html.replace("{{RAW}}", raw).replace("{{GAMES}}", "\n".join(lines)).replace("{{UPDATED}}", meta.get("updated", "not yet updated"))
os.makedirs(p("_site"), exist_ok=True)
open(p("_site", "index.html"), "w").write(html)
print("Built _site/index.html:", len(raw.split("\n")), "teams,", len(lines), "games")
