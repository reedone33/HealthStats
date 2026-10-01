#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Corrects bpMovingAvg.
#
# THE BUG
# -------
# The first version walked the readings in array order and only ever summed
# readings at or before the current index. On a day with more than one reading
# that silently left the later ones out, because they sit further along the
# array even though they share the same date. 24 of the 213 points came out
# wrong - most visibly 2025-03-11, which returned a gap when three readings
# were in fact inside its window.
#
# Within-day ordering is arbitrary - the export carries no time of day worth
# trusting - so a day's average must not depend on it.
#
# THE FIX
# -------
# The window is now the contiguous index range covering every reading whose
# DATE falls inside the trailing 14 days, same-day readings included whichever
# side of the current index they sit. Both ends only ever move forward, and a
# running total turns each window's sum into one subtraction, so this stays
# linear - it is recomputed every time the date slider moves.
# -----------------------------------------------------------------------------
import io, sys

P = "index.html"
s = io.open(P, encoding="utf-8").read()

OLD = """function bpMovingAvg(rows, key){
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
}"""

NEW = """function bpMovingAvg(rows, key){
  const len = rows.length;
  /* Dates as numbers once, up front - parsing inside the loop would mean
     thousands of Date objects for no benefit. */
  const t = rows.map(r => new Date(r.d + 'T00:00:00').getTime());
  const span = (BP_MA_DAYS - 1) * 86400000;

  /* Running totals, so the sum of any window is a single subtraction. */
  const pre = new Array(len + 1).fill(0);
  for(let i = 0; i < len; i++) pre[i + 1] = pre[i] + rows[i][key];

  const out = [];
  let lo = 0, hi = 0;

  for(let i = 0; i < len; i++){
    /* Back edge: drop readings that have aged out of the window. */
    while(t[lo] < t[i] - span) lo++;

    /* Front edge: take every reading dated on or before this one. That
       deliberately includes the OTHER readings from the same day, which sit
       further along the array - within-day order is arbitrary, so a day's
       average must not depend on it. */
    if(hi < i) hi = i;
    while(hi + 1 < len && t[hi + 1] <= t[i]) hi++;

    const n = hi - lo + 1;
    out.push(n >= BP_MA_MIN
      ? Math.round((pre[hi + 1] - pre[lo]) / n * 10) / 10
      : null);
  }
  return out;
}"""

if s.count(OLD) != 1:
    sys.exit("PATCH FAILED: found %d matches, expected 1" % s.count(OLD))

io.open(P, "w", encoding="utf-8").write(s.replace(OLD, NEW))
print("bpMovingAvg corrected")
