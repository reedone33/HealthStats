#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Blood Pressure tab: three changes
#   1. Show WHICH number (systolic, diastolic or both) put a reading in its
#      category, and state the cutoff for each.
#   2. Add a footer card explaining all five categories.
#   3. Make the shaded category bands on the line chart less transparent.
# -----------------------------------------------------------------------------
import io, sys

P = "index.html"
s = io.open(P, encoding="utf-8").read()
before = len(s)


def once(old, new, label):
    """Replace exactly one occurrence, or stop with a clear message."""
    global s
    n = s.count(old)
    if n != 1:
        sys.exit("PATCH FAILED (%s): found %d matches, expected 1" % (label, n))
    s = s.replace(old, new)


# =============================================================================
# 1. CATEGORIES — each one now knows its systolic and diastolic cutoffs
#    separately, so we can say which number was responsible.
# =============================================================================
OLD_CATS = """const BP_CATS = [
  {name:'Crisis',        test:(s,d)=> s>180 || d>120, color:'#d94f6a',
   range:'over 180 or over 120',
   note:'A hypertensive crisis. If a repeat reading five minutes later is still this high, it is treated as needing medical attention straight away.'},
  {name:'Stage 2',       test:(s,d)=> s>=140 || d>=90, color:'#f2748c',
   range:'140+ or 90+',
   note:'Stage 2 high blood pressure. Usually managed with medication alongside lifestyle changes.'},
  {name:'Stage 1',       test:(s,d)=> s>=130 || d>=80, color:'#f0b45e',
   range:'130-139 or 80-89',
   note:'Stage 1 high blood pressure. Whether it is treated with medication depends on your wider heart risk, not this number alone.'},
  {name:'Elevated',      test:(s,d)=> s>=120,          color:'#e0d06a',
   range:'120-129 and under 80',
   note:'Not high blood pressure yet, but likely to become so without a change in habits.'},
  {name:'Normal',        test:()=> true,               color:'#5ecfb1',
   range:'under 120 and under 80',
   note:'A healthy reading. Nothing to act on.'},
];"""

NEW_CATS = """const BP_CATS = [
  {name:'Crisis',   color:'#d94f6a',
   sysTest: s => s > 180,  sysCut:'above 180',
   diaTest: d => d > 120,  diaCut:'above 120',
   note:'A hypertensive crisis. If a repeat reading five minutes later is still this high, it is treated as needing medical attention straight away.'},

  {name:'Stage 2',  color:'#f2748c',
   sysTest: s => s >= 140, sysCut:'140 or above',
   diaTest: d => d >= 90,  diaCut:'90 or above',
   note:'Stage 2 high blood pressure. Usually managed with medication alongside lifestyle changes.'},

  {name:'Stage 1',  color:'#f0b45e',
   sysTest: s => s >= 130, sysCut:'130 to 139',
   diaTest: d => d >= 80,  diaCut:'80 to 89',
   note:'Stage 1 high blood pressure. Whether it is treated with medication depends on your wider heart risk, not this number alone.'},

  /* Elevated is the one category the lower number cannot cause. A diastolic of
     80 or more is already Stage 1, which is checked first. */
  {name:'Elevated', color:'#e0d06a',
   sysTest: s => s >= 120, sysCut:'120 to 129',
   diaTest: null,          diaCut:'under 80',
   note:'Not high blood pressure yet, but likely to become so without a change in habits.'},

  {name:'Normal',   color:'#5ecfb1',
   sysTest: null,          sysCut:'under 120',
   diaTest: null,          diaCut:'under 80',
   note:'A healthy reading. Nothing to act on.'},
];

/* A reading falls into the first category either number reaches. The list is
   ordered most-serious-first, so the WORSE of the two numbers always decides:
   125/95 is Stage 2 on its diastolic, even though 125 alone is only Elevated. */
const catHit = (c, s, d) => (c.sysTest && c.sysTest(s)) || (c.diaTest && c.diaTest(d));
const bpCatOf = (s, d) => BP_CATS.find(c => catHit(c, s, d)) || BP_CATS[BP_CATS.length - 1];

/* Which number put this reading in its category — 'sys', 'dia', 'both', or
   null when nothing is over a line (a Normal reading). */
function bpDriver(r){
  const c = bpCatOf(r.s, r.dia);
  const bs = !!(c.sysTest && c.sysTest(r.s));
  const bd = !!(c.diaTest && c.diaTest(r.dia));
  if(bs && bd) return 'both';
  if(bs) return 'sys';
  if(bd) return 'dia';
  return null;
}

/* The same thing in words, for the KPI card and the table. */
const DRIVER_TEXT = {
  sys:  'set by the upper number',
  dia:  'set by the lower number',
  both: 'set by both numbers',
};"""
once(OLD_CATS, NEW_CATS, "cats")

# The old classifier referenced c.test, which no longer exists.
once("const bpCat = r => BP_CATS.find(c => c.test(r.s, r.dia));",
     "const bpCat = r => bpCatOf(r.s, r.dia);",
     "bpCat")


# =============================================================================
# 2. STYLING — the highlight on a driving number, and the footer table
# =============================================================================
CSS_ANCHOR = ".catq{cursor:help;border-bottom:1px dotted currentColor;}\n"
CSS_NEW = CSS_ANCHOR + """
/* A systolic or diastolic figure that is over its line, and so is what put the
   reading in its category. Weight and an underline carry the meaning; colour
   alone would be invisible to a colour-blind reader. */
.drv{font-weight:700;border-bottom:2px solid currentColor;}
.notdrv{opacity:.55;}

/* The "set by" column — kept quiet, it is supporting detail. */
.setby{font-size:10px;color:var(--muted);white-space:nowrap;}

/* The footer key explaining every category. */
.catkey{width:100%;border-collapse:collapse;}
.catkey th{font-size:9.5px;color:var(--muted);text-transform:uppercase;
  letter-spacing:.04em;text-align:left;padding:0 8px 7px;font-weight:600;}
.catkey td{padding:8px;border-top:1px solid var(--bdr);vertical-align:top;font-size:11.5px;}
.catkey .cname{font-weight:700;white-space:nowrap;}
.catkey .cnum{font-variant-numeric:tabular-nums;white-space:nowrap;color:var(--text);}
.catkey .cjoin{color:var(--muted);font-size:10px;text-align:center;}
.catkey .cnote{color:var(--muted);line-height:1.45;}
.catkey .swatch{display:inline-block;width:9px;height:9px;border-radius:3px;
  margin-right:6px;vertical-align:middle;}
.keynote{font-size:11px;color:var(--muted);line-height:1.5;padding:10px 8px 2px;}

/* On a phone the notes column makes the table unreadably cramped, so it is
   dropped and the thresholds are left to speak for themselves. */
@media (max-width:640px){ .catkey .cnote, .catkey .hnote{display:none;} }
"""
once(CSS_ANCHOR, CSS_NEW, "css")


# =============================================================================
# 3. POPOVER — state both cutoffs explicitly rather than one prose string
# =============================================================================
once("""  el.innerHTML = `<div class="cpname" style="color:${c.color}">${c.name}</div>
    <div class="cprange">Systolic ${c.range.split(' and ')[0].split(' or ')[0]} mmHg &middot; ${c.range}</div>
    <div>${c.note}</div>`;""",
     """  el.innerHTML = `<div class="cpname" style="color:${c.color}">${c.name}</div>
    <div class="cprange">Upper (systolic) ${c.sysCut}<br>Lower (diastolic) ${c.diaCut}</div>
    <div>${c.note}</div>`;""",
     "popover")


# =============================================================================
# 4. THE FOOTER KEY — a card at the bottom of the tab
# =============================================================================
once("""      <div class="cbody"><div class="tblwrap" id="bpTable"></div></div>
    </div>`;""",
     """      <div class="cbody"><div class="tblwrap" id="bpTable"></div></div>
    </div>
    <div class="card wide">
      <div class="chead" onclick="toggleCard(this)">
        <div><div class="ctitle">What the categories mean</div>
        <div class="csub">the American Heart Association's bands, in mmHg</div></div>
        <button class="ctog">−</button>
      </div>
      <div class="cbody">
        <table class="catkey">
          <thead><tr>
            <th>Category</th><th>Upper (systolic)</th><th></th>
            <th>Lower (diastolic)</th><th class="hnote">What it means</th>
          </tr></thead>
          <tbody>${BP_CATS.map(c => `
            <tr>
              <td class="cname" style="color:${c.color}">
                <span class="swatch" style="background:${c.color}"></span>${c.name}</td>
              <td class="cnum">${c.sysCut}</td>
              <td class="cjoin">${c.name === 'Normal' || c.name === 'Elevated' ? 'and' : 'or'}</td>
              <td class="cnum">${c.diaCut}</td>
              <td class="cnote">${c.note}</td>
            </tr>`).join('')}
          </tbody>
        </table>
        <div class="keynote">
          <b>The worse of the two numbers decides.</b> A reading is placed in the
          most serious category either number reaches, so 125/95 counts as
          Stage&nbsp;2 on its lower number even though 125 on its own would only
          be Elevated. In the table above, whichever number crossed the line is
          <span class="drv">underlined</span>.
          <br><br>
          Elevated is the one band the lower number cannot cause: a diastolic of
          80 or more is already Stage&nbsp;1.
          <br><br>
          These are general adult thresholds, not a diagnosis. A single high
          reading is not the same as high blood pressure &mdash; what matters is
          the pattern over time, and what your doctor makes of it.
        </div>
      </div>
    </div>`;""",
     "footer")


# =============================================================================
# 5. THE "LATEST" KPI — say which number set the category
# =============================================================================
once("""      <div class="s">${latest.d} · ${catTerm(lc.name)}</div></div>""",
     """      <div class="s">${latest.d} · ${catTerm(lc.name)}${
        bpDriver(latest) ? '<br>' + DRIVER_TEXT[bpDriver(latest)] : ''}</div></div>""",
     "kpi")


# =============================================================================
# 6. THE TABLE — highlight the driving number, and name it in a new column
# =============================================================================
once("""    '<table><thead><tr><th>Date</th><th>Systolic</th><th>Diastolic</th><th>Category</th></tr></thead><tbody>' +
    rows.slice().reverse().map(r => {
      const c = bpCat(r);
      return `<tr><td>${r.d}</td><td>${r.s}</td><td>${r.dia}</td>
        <td><span class="pill catq" data-cat="${c.name}" style="background:${c.color}22;color:${c.color}">${c.name}</span></td></tr>`;
    }).join('') + '</tbody></table>';""",
     """    '<table><thead><tr><th>Date</th><th>Upper</th><th>Lower</th><th>Category</th><th>Set by</th></tr></thead><tbody>' +
    rows.slice().reverse().map(r => {
      const c = bpCat(r);
      const drv = bpDriver(r);
      /* Underline whichever number crossed the line; fade the one that didn't,
         so the reason for the category reads at a glance. */
      const sysCls = drv === 'sys' || drv === 'both' ? 'drv' : (drv ? 'notdrv' : '');
      const diaCls = drv === 'dia' || drv === 'both' ? 'drv' : (drv ? 'notdrv' : '');
      const label  = drv === 'both' ? 'both' : drv === 'sys' ? 'upper'
                   : drv === 'dia' ? 'lower' : '—';
      return `<tr><td>${r.d}</td>
        <td><span class="${sysCls}" style="color:${drv === 'sys' || drv === 'both' ? c.color : ''}">${r.s}</span></td>
        <td><span class="${diaCls}" style="color:${drv === 'dia' || drv === 'both' ? c.color : ''}">${r.dia}</span></td>
        <td><span class="pill catq" data-cat="${c.name}" style="background:${c.color}22;color:${c.color}">${c.name}</span></td>
        <td class="setby">${label}</td></tr>`;
    }).join('') + '</tbody></table>';""",
     "table")


# =============================================================================
# 7. THE CHART BANDS — roughly double the opacity so they actually read
# =============================================================================
once("""        {from:0,   to:120, c:'rgba(94,207,177,.07)'},
        {from:120, to:130, c:'rgba(224,208,106,.07)'},
        {from:130, to:140, c:'rgba(240,180,94,.08)'},
        {from:140, to:400, c:'rgba(242,116,140,.08)'},""",
     """        {from:0,   to:120, c:'rgba(94,207,177,.15)'},
        {from:120, to:130, c:'rgba(224,208,106,.15)'},
        {from:130, to:140, c:'rgba(240,180,94,.17)'},
        {from:140, to:400, c:'rgba(242,116,140,.17)'},""",
     "bands")


io.open(P, "w", encoding="utf-8").write(s)
print("Patched index.html — %d -> %d bytes" % (before, len(s)))
