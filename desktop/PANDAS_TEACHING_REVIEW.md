# Linux pandas teaching review — 4.7.6-pandas-preview

## What changed

The original lessons presented only a short summary and one worked problem.
Their applications also required syntax that had not been taught (notably
Series list selection and sum, Index.tolist, and DataFrame.loc before the loc
unit). The assessment tasks themselves were retained.

The 26 existing pandas units now contain 81 independent guided examples. Each
page explains the syntax and arguments, gives runnable code with different data
from the assessment, describes the expected result, and offers result checks.

- Entry: import alias, calls and indexing, strings, lists/dictionaries, keyword
  arguments, assignment versus display, Series versus DataFrame.
- Selection: labels versus positions, list selection, return dimensions, axis
  direction, cell updates, filters, missing values, tolist.
- Tables: concat policies, keyed joins, duplicate keys, suffixes, index joins,
  pivot versus aggregation, compound indexes, group/filter order.
- Dates and charts: date Series versus DatetimeIndex, year/month grouping,
  multi-function aggregation, plot/Axes/Figure, subplot selection.

The UI uses the actual number of learning pages instead of a fixed two. It
stores the page number as existing learning metadata, without storing typed
code or temporary files. Completed and passed unit records are unchanged.
Guided result checks do **not** grant exercise/unit completion.

## How to review

Open Python · 데이터, choose pandas, then a unit. If an old saved position opens
an application task, use **문법 다시 배우기 (F3)** to return to that unit's first
explanation. This preserves completed progress but clears the current temporary
exercise after confirmation when code is present.

Read a page, type its example (or use **소단계 코드 넣기**), execute with
Shift+Enter, and compare the output with **결과 읽기**. F5 checks the example's
results. F6 opens the next page; the final page leads to the original full example
and applications. Pages use independent examples; moving between them clears
temporary variables and editor contents. The learning position remains saved.

## Verification scope

- All 81 newly authored examples executed from a fresh namespace and again in
  the same namespace against pandas 2.3.3; expected objects/values were checked.
- Static audit: APIs/keyword arguments in pandas applications and reviews have
  preceding teaching examples. This checks syntax coverage, not a claim that
  every possible pandas feature is taught.
- Existing 95 unit identities and assessment tasks preserved.
- Focused UI tests: five-page navigation/resume, isolated CSV fixtures, repeated
  correction without restart, no completion credit for guided examples,
  returning to explanations, legacy two-page progress and fixture presentation.
- The packaged UI check covers the first and last Series pages in the bundled
  worker, screenshot capture, embedded-window behavior, and shutdown cleanup.
- No replay of the full Linux/Docker/ROS course, no VM rebuild, no Windows or
  Android build. NAS synchronization from the preceding Linux preview remains.

## References

Authored small examples and checks are in `python_teaching/pandas_guidance.py`.
Library behavior was checked against the bundled version's official documents:

- [pandas 2.3: introduction](https://pandas.pydata.org/pandas-docs/version/2.3/user_guide/10min.html)
- [Indexing and selecting](https://pandas.pydata.org/pandas-docs/version/2.3/user_guide/indexing.html)
- [Grouping and aggregation](https://pandas.pydata.org/pandas-docs/version/2.3/user_guide/groupby.html)

Existing lecture page attribution remains attached to each lesson. The added
syntax explanations are teaching support, not claims of new lecture content.
