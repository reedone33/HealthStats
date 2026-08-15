#!/usr/bin/env python3
# Adds tap-or-hover explanations to the blood pressure category names.
import io, sys, re

P = "index.html"
s = io.open(P, encoding="utf-8").read()
orig = s


def once(old, new, label):
    """Replace exactly one occurrence, or stop with a clear message."""
    global s
    if s.count(old) != 1:
        sys.exit("PATCH FAILED (%s): found %d matches, expected 1" % (label, s.count(old)))
    s = s.replace(old, new)


# ---------------------------------------------------------------------------
# 1. STYLING for the underlined term and the popover bubble
# ---------------------------------------------------------------------------
CSS_ANCHOR = ".pill{display:inline-block;padding:1px 7px;border-radius:20px;font-size:10px;font-weight:600;}\n"
CSS_NEW = CSS_ANCHOR + """
/* --- Blood pressure category explanations --------------------------------
   Any element carrying data-cat becomes tappable (phone) or hoverable (Mac)
   and shows a small bubble describing that AHA category. A dotted underline
   hints that there is something to tap. */
.catq{cursor:help;border-bottom:1px dotted currentColor;}

/* The bubble itself. Only one exists on the page; it is moved next to
   whichever term was tapped, rather than one bubble per pill. */
#catpop{
  position:absolute; z-index:60; max-width:250px; display:none;
  background:var(--card); border:1px solid var(--bdr); border-radius:11px;
  padding:10px 12px; box-shadow:0 8px 26px rgba(0,0,0,.45);
  font-size:11.5px; line-height:1.45; color:var(--text);
}
#catpop.on{display:block;}
#catpop .cpname{font-weight:700; font-size:12.5px; margin-bottom:3px;}
#catpop .cprange{color:var(--muted); font-size:10.5px; margin-bottom:6px;}
"""
once(CSS_ANCHOR, CSS_NEW, "css")


# ---------------------------------------------------------------------------
# 2. DESCRIPTIONS on each category, alongside the existing test and colour
# ---------------------------------------------------------------------------
CATS_OLD = """const BP_CATS = [
  {name:'Crisis',        test:(s,d)=> s>180 || d>120, color:'#d94f6a'},
  {name:'Stage 2',       test:(s,d)=> s>=140 || d>=90, color:'#f2748c'},
  {name:'Stage 1',       test:(s,d)=> s>=130 || d>=80, color:'#f0b45e'},
  {name:'Elevated',      test:(s,d)=> s>=120,          color:'#e0d06a'},
  {name:'Normal',        test:()=> true,               color:'#5ecfb1'},
];"""

CATS_NEW = """const BP_CATS = [
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
];

/* A reading is classified by whichever number is WORSE, which is why the list
   above is checked most-serious-first — 125/95 is Stage 2 on its diastolic
   even though its systolic alone would read as Elevated. */
const catByName = n => BP_CATS.find(c => c.name === n);

/* --- The popover ----------------------------------------------------------
   One bubble, reused. Clicking anything with data-cat opens it; clicking
   anywhere else, pressing Escape, or scrolling closes it. Using click rather
   than :hover is what makes this work on a phone, where there is no hover. */
function catPop(){
  let el = document.getElementById('catpop');
  if(!el){
    el = document.createElement('div');
    el.id = 'catpop';
    document.body.appendChild(el);
  }
  return el;
}

function hideCatPop(){ catPop().classList.remove('on'); }

function showCatPop(target){
  const c = catByName(target.dataset.cat);
  if(!c) return;
  const el = catPop();
  el.innerHTML = `<div class="cpname" style="color:${c.color}">${c.name}</div>
    <div class="cprange">Systolic ${c.range.split(' and ')[0].split(' or ')[0]} mmHg &middot; ${c.range}</div>
    <div>${c.note}</div>`;
  el.classList.add('on');

  /* Position it just under the term, nudged back on screen if it would
     otherwise run off the right edge on a narrow phone. */
  const r = target.getBoundingClientRect();
  const w = el.offsetWidth;
  let left = r.left + window.scrollX;
  const maxLeft = window.scrollX + document.documentElement.clientWidth - w - 10;
  if(left > maxLeft) left = maxLeft;
  if(left < window.scrollX + 10) left = window.scrollX + 10;
  el.style.left = left + 'px';
  el.style.top  = (r.bottom + window.scrollY + 7) + 'px';
}

/* Listeners are attached once, to the document, so they keep working even
   though the pills are rebuilt every time the date range changes. */
document.addEventListener('click', e => {
  const t = e.target.closest('[data-cat]');
  if(t){ e.stopPropagation(); showCatPop(t); }
  else { hideCatPop(); }
});
document.addEventListener('keydown', e => { if(e.key === 'Escape') hideCatPop(); });
window.addEventListener('scroll', hideCatPop, {passive:true});

/* On a Mac, hovering is quicker than clicking, so do that too. */
document.addEventListener('mouseover', e => {
  const t = e.target.closest('[data-cat]');
  if(t) showCatPop(t);
});
document.addEventListener('mouseout', e => {
  if(e.target.closest('[data-cat]')) hideCatPop();
});

/* Wraps a category name in the tappable, underlined markup. */
const catTerm = (name, extra='') =>
  `<span class="catq" data-cat="${name}"${extra}>${name}</span>`;"""
once(CATS_OLD, CATS_NEW, "cats")


# ---------------------------------------------------------------------------
# 3. The "Latest" KPI card — make its category name tappable
# ---------------------------------------------------------------------------
once("""      <div class="s">${latest.d} · ${lc.name}</div></div>""",
     """      <div class="s">${latest.d} · ${catTerm(lc.name)}</div></div>""",
     "kpi")


# ---------------------------------------------------------------------------
# 4. The doughnut legend — make each category name tappable
# ---------------------------------------------------------------------------
once("""    counts.map(x => `<div class="lg"><i style="background:${x.c.color}"></i>${x.c.name} (${x.n})</div>`).join('');""",
     """    counts.map(x => `<div class="lg"><i style="background:${x.c.color}"></i>${catTerm(x.c.name)} (${x.n})</div>`).join('');""",
     "legend")


# ---------------------------------------------------------------------------
# 5. The table pills — make every row's category tappable
# ---------------------------------------------------------------------------
once("""        <td><span class="pill" style="background:${c.color}22;color:${c.color}">${c.name}</span></td></tr>`;""",
     """        <td><span class="pill catq" data-cat="${c.name}" style="background:${c.color}22;color:${c.color}">${c.name}</span></td></tr>`;""",
     "pills")


# ---------------------------------------------------------------------------
# 6. A hint in the card subtitle, so the feature is discoverable
# ---------------------------------------------------------------------------
once("""        <div class="csub">how your readings distribute across the AHA bands</div></div>""",
     """        <div class="csub">how your readings distribute across the AHA bands &mdash; tap a category name to see what it means</div></div>""",
     "hint")

io.open(P, "w", encoding="utf-8").write(s)
print("Patched index.html — %d bytes -> %d bytes" % (len(orig), len(s)))
