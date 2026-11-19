# Partner deliverable QA

Demo page: https://pg2342-hub.github.io/partner-deliverable-qa/

Within co-delivers through consulting partners. The partner's consultants run the discovery sprint for a customer, and Within's delivery lead holds what they produce to Within's standard before it reaches the customer's controller. This tool is that check: the delivery lead runs it on the partner's discovery deliverable for a 30-day month-end close sprint, and partners can run it on their own work before handing it over. It checks the deliverable against the close calendar and answers three questions:

1. **Is it ready for the readout?** Eight checks, all must pass.
2. **If not, what goes back to the partner?** One specific line per problem, written so the partner can act on it.
3. **Which fixes come first?** Ranked by hours saved per close per unit of effort, with any savings claim capped at the hands-on hours the map actually shows.

| Check | Standard |
|---|---|
| C1 Coverage | At least 90% of close-calendar tasks mapped, for corporate and the acquired business separately |
| C2 Complete steps | Every step has an owner, a system, start and end day, and hands-on hours |
| C3 Timing vs calendar | No step ends after its task's due day unless the map says why |
| C4 Steps tie to the calendar | Every step belongs to a task on the close calendar |
| C5 Map confirmed before ranking | The close manager confirmed the map before fixes were ranked |
| C6 Fixes trace to the map | Every fix points only at steps that exist in the map |
| C7 Savings fit the map | Hours saved per close never exceed the hands-on hours of the steps a fix touches |
| C8 Fixes are owned and sized | Every fix has an owner and an effort size (S, M or L) |

C5 is the one I care about most: a ranked list only earns the controller's trust once the people who run the close agree the map matches what they do.

## Run it

Python 3.9 or newer, standard library only.

```
python qa.py                              # partner draft (exit code 1: send back)
python qa.py --data data/after_fixes      # same deliverable after fixes (exit code 0)
python qa.py --out report.md --json result.json
python -m unittest discover -s tests
python docs/build_page.py                 # rebuild the demo page
```

On the partner draft, all 9 planted problems are flagged and 0 of 8 checks pass: the acquired business is only 71% mapped (4 tasks missing), two steps lack an owner or system, one step runs past its due day with no reason, one step points at a task that is not on the calendar, there is no record of the close manager confirming the map, one fix points at a step that does not exist, one fix claims 30 hours saved where its steps total 23, and one fix has no owner. After the fixes, 8 of 8 pass. See `sample_report.md` and `sample_report_after_fixes.md`.

## Your own deliverable

Put three files in a folder and pass `--data` (and `--calendar` for your own close calendar):

- `process_map.csv`: step_id, task_id, unit, step, owner_role, system, start_business_day, end_business_day, hands_on_hours, exception_notes
- `fix_ranking.csv`: fix_id, fix, step_ids (separated by `;`), hours_saved_per_close, effort (S/M/L), owner_role, evidence
- `signoff.json`: map_confirmed_by_role, map_confirmed_on, ranking_presented_on (ISO dates)

## Data and numbers

All data is synthetic: a 38-task close calendar for a corporate entity plus an acquired business, written to follow the structure of my 30-day close sprint plan. No customer data. Value per year = hours counted × 12 closes × $40.23/hr, the BLS median accountant pay of $83,680 divided by 2,080 hours, base pay only. It is team time handed back, not budget saved.
