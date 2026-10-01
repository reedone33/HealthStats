#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Blood pressure trend chart: add a 14-day moving average to both lines.
#
# WHY A CALENDAR WINDOW, NOT "THE LAST N READINGS"
# ------------------------------------------------
# Blood pressure readings are not daily. There are 213 of them across 185 days:
# usually one a day, sometimes four, and in early 2025 there are 14 gaps longer
# than a week. Averaging "the last 14 readings" would mean that in the sparse
# stretch a single point was being averaged with others up to two months old,
# and the line would lag badly. Averaging everything inside the trailing 14
# CALENDAR days keeps the window honest: in a dense stretch it holds ~14
# readings, and in a sparse one it holds few, which is the truth about how much
# was measured.
#
# A window holding fewer than MIN_READINGS values produces null rather than a
# number, so the average line breaks instead of drawing a confident-looking
# trend from one reading. This matches how the sleep charts already behave.
# -----------------------------------------------------------------------------
import io, sys

P = "index.html"
s = io.open(P, encoding="utf-8").read()
before = len(s)


def once(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit("PATCH FAILED (%s): found %d matches, expected 1" % (label, n))
    s = s.replace(old, new)


# =============================================================================
# 1. THE CALCULATION
#    Added just above renderBP, next to the other blood pressure helpers.
# =============================================================================
ANCHOR = "/* Only the readings inside the currently selected date range. */"

NEW = """/* --- 14-day moving average over irregularly spaced readings ---------------
   For each reading, average every reading whose date falls inside the trailing
   WINDOW_DAYS calendar days (inclusive of the reading's own day).

   Readings come in date order, so a two-pointer walk is enough: `lo` only ever
   moves forward. That keeps this linear rather than re-scanning the whole list
   for every point, which matters because the array is rebuilt every time the
   date slider moves.

   Returns null where too few readings fall in the window, so the line breaks
   over a sparse stretch rather than implying a trend that isn't measured. */
const BP_MA_DAYS = 14;   // the window, in calendar days
const BP_MA_MIN  = 3;    // fewest readings that may produce a value

function bpMovingAvg(rows, key){
  const out = [];
  /* Dates as numbers once, up front - parsing inside the loop would mean
     thousands of Date objects for no benefit. */
  const t = rows.map(r => new Date(r.d + 'T00:00:00').getTime());
  const span = (BP_MA_DAYS - 1) * 86400000;

  let lo = 0, sum = 0, n = 0;
  for(let hi = 0; hi < rows.length; hi++){
    sum += rows[hi][key]; n++;

    /* Drop anything that has fallen out of the back of the window. */
    while(t[lo] < t[hi] - span){ sum -= rows[lo][key]; n--; lo++; }

    out.push(n >= BP_MA_MIN ? Math.round(sum / n * 10) / 10 : null);
  }
  return out;
}

/* Only the readings inside the currently selected date range. */"""

once(ANCHOR, NEW, "helper")


# =============================================================================
# 2. THE CHART
#    Raw readings step back; the two averages are drawn on top.
# =============================================================================
once("""    data:{ labels: rows.map(r => r.d), datasets:[
      {label:'Systolic',  data: rows.map(r => r.s),   borderColor:CV('sys'),
       backgroundColor:CV('sys'), borderWidth:2, pointRadius:2.5, tension:.25},
      {label:'Diastolic', data: rows.map(r => r.dia), borderColor:CV('dia'),
       backgroundColor:CV('dia'), borderWidth:2, pointRadius:2.5, tension:.25},
    ]},""",
     """    /* Raw readings sit underneath at reduced weight; the moving averages are
       the bold lines on top. With 200+ noisy points, four lines at equal
       weight is unreadable - the trend has to win the eye. `order` controls
       the draw order: higher numbers are drawn first, so end up behind. */
    data:{ labels: rows.map(r => r.d), datasets:[
      {label:'Systolic',  data: rows.map(r => r.s),   borderColor:CV('sys') + '55',
       backgroundColor:CV('sys') + '55', borderWidth:1, pointRadius:1.5, tension:.25, order:3},
      {label:'Diastolic', data: rows.map(r => r.dia), borderColor:CV('dia') + '55',
       backgroundColor:CV('dia') + '55', borderWidth:1, pointRadius:1.5, tension:.25, order:3},

      {label:'Systolic 14-day avg',  data: bpMovingAvg(rows, 's'),
       borderColor:CV('sys'), borderWidth:2.6, pointRadius:0, tension:.35,
       spanGaps:false, order:1},
      {label:'Diastolic 14-day avg', data: bpMovingAvg(rows, 'dia'),
       borderColor:CV('dia'), borderWidth:2.6, pointRadius:0, tension:.35,
       spanGaps:false, order:1},
    ]},""",
     "datasets")


# =============================================================================
# 3. THE LEGEND AND SUBTITLE
# =============================================================================
once("""        <div class="legend">
          <div class="lg"><i style="background:${CV('sys')}"></i>Systolic (upper)</div>
          <div class="lg"><i style="background:${CV('dia')}"></i>Diastolic (lower)</div>
        </div>""",
     """        <div class="legend">
          <div class="lg"><i style="background:${CV('sys')};opacity:.4"></i>Systolic readings</div>
          <div class="lg"><i style="background:${CV('sys')}"></i>Systolic 14-day avg</div>
          <div class="lg"><i style="background:${CV('dia')};opacity:.4"></i>Diastolic readings</div>
          <div class="lg"><i style="background:${CV('dia')}"></i>Diastolic 14-day avg</div>
        </div>""",
     "legend")

once("""        <div class="csub">shaded bands mark the AHA categories for systolic pressure</div></div>""",
     """        <div class="csub">bold lines are a 14-day average &mdash; they break where too few readings were taken to average honestly. Shaded bands mark the AHA categories for systolic pressure.</div></div>""",
     "subtitle")


io.open(P, "w", encoding="utf-8").write(s)
print("Patched index.html — %d -> %d bytes" % (before, len(s)))
