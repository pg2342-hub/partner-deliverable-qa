"""Partner deliverable QA for a 30-day month-end close sprint.

Reads a partner-produced discovery deliverable (process map, fix ranking,
sign-off record) and checks it against the close calendar before it goes
to the customer's controller. Prints a readout-ready verdict, the checks,
a send-back list for the partner, and the fixes ranked by value per effort.

Standard library only. All bundled data is synthetic.
"""
import argparse
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COVERAGE_TARGET = 0.90
HOURLY_RATE = 83680 / 2080  # BLS median accountant pay, base only (about $40.23)
CLOSES_PER_YEAR = 12
EFFORT_WEIGHT = {"S": 1, "M": 2, "L": 3}
EFFORT_LABEL = {"S": "Small", "M": "Medium", "L": "Large"}
REQUIRED_STEP_FIELDS = ["owner_role", "system", "start_business_day", "end_business_day", "hands_on_hours"]

CHECKS = [
    ("C1", "Every part of the close is mapped", "At least 90% of the close calendar's tasks are in the map, for corporate and the acquired business separately"),
    ("C2", "Every step is filled in", "Each step has an owner, a system, start and end days, and hands-on hours"),
    ("C3", "Steps finish on time", "No step finishes after its task is due, unless the map explains why"),
    ("C4", "Every step matches the calendar", "Each step belongs to a task on the close calendar"),
    ("C5", "Close manager confirmed the map first", "The close manager agreed the map matches how the close really runs before any fixes were ranked"),
    ("C6", "Every fix points at real steps", "Each fix names only steps that are in the map"),
    ("C7", "Savings claims are believable", "No fix claims more hours saved than the steps it touches actually take"),
    ("C8", "Every fix has an owner and a size", "Each fix has an owner and an effort size (small, medium or large)"),
]


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load(folder, calendar_path):
    return {
        "calendar": read_csv(calendar_path),
        "steps": read_csv(os.path.join(folder, "process_map.csv")),
        "fixes": read_csv(os.path.join(folder, "fix_ranking.csv")),
        "signoff": json.load(open(os.path.join(folder, "signoff.json"), encoding="utf-8")),
    }


def num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def run_checks(d):
    cal = {t["task_id"]: t for t in d["calendar"]}
    steps = {s["step_id"]: s for s in d["steps"]}
    issues = {cid: [] for cid, _, _ in CHECKS}
    coverage = {}

    # C1 coverage per unit
    mapped = {s["task_id"] for s in d["steps"]}
    for unit in sorted({t["unit"] for t in d["calendar"]}):
        tasks = [t for t in d["calendar"] if t["unit"] == unit]
        hit = [t for t in tasks if t["task_id"] in mapped]
        share = len(hit) / len(tasks)
        coverage[unit] = {"mapped": len(hit), "total": len(tasks), "share": round(share, 3)}
        if share < COVERAGE_TARGET:
            missing = ", ".join(t["task"] for t in tasks if t["task_id"] not in mapped)
            issues["C1"].append(f"{unit}: only {len(hit)} of {len(tasks)} close tasks are mapped ({share:.0%}). Add: {missing}")

    for s in d["steps"]:
        sid = s["step_id"]
        # C2 completeness
        blank = [f for f in REQUIRED_STEP_FIELDS if not str(s.get(f, "")).strip()]
        if blank:
            names = {"owner_role": "owner", "system": "system", "start_business_day": "start day",
                     "end_business_day": "end day", "hands_on_hours": "hands-on hours"}
            issues["C2"].append(f"\u201c{s['step']}\u201d ({s['unit']}) has no {' or '.join(names[f] for f in blank)} listed")
        task = cal.get(s["task_id"])
        # C4 ties to calendar
        if task is None:
            issues["C4"].append(f"\u201c{s['step']}\u201d isn't tied to any task on the close calendar. Attach it to the task it belongs to")
            continue
        # C3 timing
        end, due = num(s["end_business_day"]), num(task["due_business_day"])
        if end is not None and due is not None and end > due and not s.get("exception_notes", "").strip():
            issues["C3"].append(f"\u201c{s['step']}\u201d finishes on business day {end:g}, but its task is due on day {due:g}, and the map doesn't say why")

    # C5 sign-off before ranking
    so = d["signoff"]
    confirmed, presented = so.get("map_confirmed_on", ""), so.get("ranking_presented_on", "")
    if not (so.get("map_confirmed_by_role") and confirmed):
        issues["C5"].append("Nothing shows the close manager confirmed the map. Walk them through it before the ranking goes to the controller")
    elif presented and confirmed > presented:
        issues["C5"].append(f"The map was confirmed on {confirmed}, after the ranking was presented on {presented}")

    ranked = []
    for fx in d["fixes"]:
        fid = fx["fix_id"]
        ids = [x.strip() for x in fx["step_ids"].split(";") if x.strip()]
        unknown = [x for x in ids if x not in steps]
        # C6 traceability
        if unknown:
            issues["C6"].append(f"\u201c{fx['fix']}\u201d points at a step that isn't in the map. Point it at the right step or drop it")
        mapped_hours = sum(num(steps[x]["hands_on_hours"]) or 0 for x in ids if x in steps)
        saved = num(fx["hours_saved_per_close"]) or 0
        # C7 plausibility
        if saved > mapped_hours:
            issues["C7"].append(f"\u201c{fx['fix']}\u201d claims {saved:g} hours saved per close, but the steps it touches only take {mapped_hours:g} hours")
        # C8 owned and sized
        gaps = []
        if not fx.get("owner_role", "").strip():
            gaps.append("an owner")
        if fx.get("effort", "").strip() not in EFFORT_WEIGHT:
            gaps.append("an effort size")
        if gaps:
            issues["C8"].append(f"\u201c{fx['fix']}\u201d needs {' and '.join(gaps)}")
        counted = min(saved, mapped_hours)
        weight = EFFORT_WEIGHT.get(fx.get("effort", "").strip(), 3)
        ranked.append({
            "fix_id": fid, "fix": fx["fix"], "effort": fx.get("effort", ""),
            "effort_label": EFFORT_LABEL.get(fx.get("effort", "").strip(), ""),
            "owner": fx.get("owner_role", ""), "claimed_hours": saved,
            "mapped_hours": mapped_hours, "counted_hours": counted,
            "annual_value": round(counted * CLOSES_PER_YEAR * HOURLY_RATE),
            "score": round(counted / weight, 2),
        })
    ranked.sort(key=lambda r: (-r["score"], r["fix_id"]))

    results = []
    for cid, name, standard in CHECKS:
        results.append({"id": cid, "name": name, "standard": standard,
                        "passed": not issues[cid], "issues": issues[cid]})
    ready = all(r["passed"] for r in results)
    return {"ready": ready, "checks": results, "coverage": coverage, "ranked_fixes": ranked,
            "issue_count": sum(len(v) for v in issues.values()),
            "total_mapped_hours": sum(num(s["hands_on_hours"]) or 0 for s in d["steps"])}


def to_markdown(name, r):
    out = [f"# Partner deliverable QA: {name}", ""]
    verdict = "READOUT-READY" if r["ready"] else "SEND BACK TO PARTNER"
    passed = sum(c["passed"] for c in r["checks"])
    out += [f"**Verdict: {verdict}** ({passed} of {len(r['checks'])} checks pass, {r['issue_count']} issues)", ""]
    for unit, c in r["coverage"].items():
        out.append(f"- {unit} coverage: {c['mapped']} of {c['total']} tasks ({c['share']:.0%})")
    out += ["", "## Checks", "", "| Check | Standard | Result |", "|---|---|---|"]
    for c in r["checks"]:
        out.append(f"| {c['name']} | {c['standard']} | {'PASS' if c['passed'] else 'FAIL'} |")
    if not r["ready"]:
        out += ["", "## Send back to the partner", ""]
        for c in r["checks"]:
            for i in c["issues"]:
                out.append(f"- {c['name']}: {i}")
    out += ["", "## Fixes, best value for the effort first", "",
            "| Rank | Fix | Effort | Hours saved per close | Value per year | Note |", "|---|---|---|---|---|---|"]
    for n, f in enumerate(r["ranked_fixes"], 1):
        note = "" if f["claimed_hours"] <= f["mapped_hours"] else f"claimed {f['claimed_hours']:g}, counted {f['counted_hours']:g} (all the mapped hours)"
        out.append(f"| {n} | {f['fix']} | {f['effort_label'] or 'missing'} | {f['counted_hours']:g} | ${f['annual_value']:,} | {note} |")
    out += ["", f"Value per year = hours counted x {CLOSES_PER_YEAR} closes x ${HOURLY_RATE:.2f}/hr (BLS median accountant pay, base only). It is team time handed back, not budget saved.", ""]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", default=os.path.join(HERE, "data", "partner_draft"),
                    help="folder with process_map.csv, fix_ranking.csv, signoff.json")
    ap.add_argument("--calendar", default=os.path.join(HERE, "data", "close_calendar.csv"))
    ap.add_argument("--out", help="write the report as markdown")
    ap.add_argument("--json", help="write the result as JSON")
    a = ap.parse_args(argv)
    r = run_checks(load(a.data, a.calendar))
    md = to_markdown(os.path.basename(os.path.normpath(a.data)), r)
    print(md)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(md)
    if a.json:
        json.dump(r, open(a.json, "w", encoding="utf-8"), indent=2)
    return 0 if r["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
