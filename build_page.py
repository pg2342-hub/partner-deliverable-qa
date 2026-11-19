"""Rebuilds docs/index.html from the bundled data: python docs/build_page.py"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import qa  # noqa: E402

cal = os.path.join(ROOT, "data", "close_calendar.csv")
data = {}
for key in ("partner_draft", "after_fixes"):
    d = qa.load(os.path.join(ROOT, "data", key), cal)
    r = qa.run_checks(d)
    r["steps"] = d["steps"]
    data[key] = r
tpl = open(os.path.join(ROOT, "docs", "template.html"), encoding="utf-8").read()
html = tpl.replace("/*DATA*/", "const DATA = " + json.dumps(data) + ";")
open(os.path.join(ROOT, "docs", "index.html"), "w", encoding="utf-8").write(html)
print("wrote docs/index.html")
