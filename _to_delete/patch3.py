#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Adds a full-screen view to every chart card.
#
# HOW IT WORKS, in one paragraph: rather than building a second copy of each
# chart, the whole CARD ELEMENT is physically moved into a full-screen overlay
# and moved back when you close it. Chart.js mutates the config object it is
# given, so handing the same config to a second chart does not work; moving the
# element sidesteps that completely. It also means this works for every card
# without knowing anything about what is inside it.
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
# 1. STYLING — the expand button and the overlay
# =============================================================================
CSS_ANCHOR = ".pill{display:inline-block;padding:1px 7px;border-radius:20px;font-size:10px;font-weight:600;}\n"
CSS_NEW = CSS_ANCHOR + """
/* --- Full-screen chart view ----------------------------------------------
   The expand button lives in the card header, next to the collapse toggle. */
.cbtns{display:flex;align-items:center;gap:2px;flex:0 0 auto;}
.cfs{
  background:none;border:none;color:var(--muted);cursor:pointer;
  font-size:13px;line-height:1;padding:4px 6px;border-radius:6px;
}
.cfs:hover{color:var(--text);background:rgba(255,255,255,.06);}

/* The overlay. Covers everything, including the sticky header and tab bar.
   inset:0 pins it to the viewport, and the safe-area padding keeps the close
   button clear of the iPhone's notch and home indicator. */
#fsov{
  position:fixed;inset:0;z-index:200;display:none;
  background:var(--bg);
  padding:calc(var(--safe-t) + 8px) 12px calc(var(--safe-b) + 12px);
  overflow:auto;
}
#fsov.on{display:flex;flex-direction:column;}

.fsbar{display:flex;align-items:center;justify-content:flex-end;
  gap:8px;margin-bottom:6px;flex:0 0 auto;}
.fsclose{
  background:var(--card);border:1px solid var(--bdr);color:var(--text);
  font-size:12px;padding:7px 14px;border-radius:9px;cursor:pointer;
}
.fsclose:hover{border-color:var(--rem);color:var(--rem);}

/* Where the moved card lands. It grows to fill whatever is left. */
#fshost{flex:1 1 auto;display:flex;flex-direction:column;min-height:0;}
#fshost .card{flex:1 1 auto;display:flex;flex-direction:column;min-height:0;}
#fshost .cbody{flex:1 1 auto;display:flex;flex-direction:column;min-height:0;}

/* The whole point: let the chart use the height that is going spare, instead
   of the fixed 230px it has in the grid. */
#fshost .chart-box{height:auto !important;flex:1 1 auto;min-height:200px;}

/* Collapsing a card while it is full screen would leave an empty box, and the
   expand button is meaningless in there. */
#fshost .ctog, #fshost .cfs{display:none;}

/* The date range bar comes along, but without its sticky positioning - inside
   the overlay there is nothing for it to stick to. */
#fsov .rangebar{position:static;top:auto;border-radius:11px;border:1px solid var(--bdr);
  margin-bottom:8px;flex:0 0 auto;}

/* Stop the page behind from scrolling while the overlay is open. */
body.fslock{overflow:hidden;}
"""
once(CSS_ANCHOR, CSS_NEW, "css")


# =============================================================================
# 2. THE OVERLAY MARKUP — one of these for the whole page
# =============================================================================
once("<main>", """<!-- Full-screen chart overlay. Empty until a chart is expanded into it. -->
<div id="fsov" aria-hidden="true">
  <div class="fsbar">
    <button class="fsclose" id="fsclose">&times;&nbsp; Close</button>
  </div>
  <div id="fshost"></div>
</div>

<main>""", "overlay")


# =============================================================================
# 3. THE EXPAND BUTTON — added to the chart-card header
# =============================================================================
# Cards built from SPECS.
once("""      <div><div class="ctitle">${spec.title}</div><div class="csub">${spec.sub}</div></div>
      <button class="ctog">−</button>""",
     """      <div><div class="ctitle">${spec.title}</div><div class="csub">${spec.sub}</div></div>
      <div class="cbtns">
        <button class="cfs" title="Full screen" aria-label="Full screen">&#9974;</button>
        <button class="ctog">−</button>
      </div>""",
     "spec card button")

# The two hand-written Blood Pressure chart cards. The readings table and the
# category key are not charts, so they are deliberately left alone.
once("""        <div><div class="ctitle">Systolic & diastolic over time</div>
        <div class="csub">shaded bands mark the AHA categories for systolic pressure</div></div>
        <button class="ctog">−</button>""",
     """        <div><div class="ctitle">Systolic & diastolic over time</div>
        <div class="csub">shaded bands mark the AHA categories for systolic pressure</div></div>
        <div class="cbtns">
          <button class="cfs" title="Full screen" aria-label="Full screen">&#9974;</button>
          <button class="ctog">−</button>
        </div>""",
     "bp trend button")

once("""        <div><div class="ctitle">Readings by category</div>
        <div class="csub">how your readings distribute across the AHA bands &mdash; tap a category name to see what it means</div></div>
        <button class="ctog">−</button>""",
     """        <div><div class="ctitle">Readings by category</div>
        <div class="csub">how your readings distribute across the AHA bands &mdash; tap a category name to see what it means</div></div>
        <div class="cbtns">
          <button class="cfs" title="Full screen" aria-label="Full screen">&#9974;</button>
          <button class="ctog">−</button>
        </div>""",
     "bp dough button")


# =============================================================================
# 4. THE BEHAVIOUR
# =============================================================================
ANCHOR = """/* Collapse or expand a card. Charts are resized afterwards so they redraw at
   the right size rather than staying squashed. */
function toggleCard(head){"""

NEW_FN = """/* --- Full-screen chart view ------------------------------------------------
   Rather than drawing a second copy of the chart, the card element itself is
   moved into the overlay and moved back on close. A placeholder marks the spot
   it came from, so it always returns to the right position in the grid even
   though the cards are otherwise identical. */

let FS_OPEN = null;   // the card currently blown up, or null

/* Move an element into a new parent, leaving a marker behind so it can be put
   back exactly where it was. */
function moveInto(el, host){
  const mark = document.createElement('div');
  mark.style.display = 'none';
  el.parentNode.insertBefore(mark, el);
  el._fsHome = mark;
  host.appendChild(el);
}

function restoreMoved(el){
  const mark = el._fsHome;
  if(mark && mark.parentNode){
    mark.parentNode.insertBefore(el, mark);
    mark.remove();
  }
  el._fsHome = null;
}

/* Chart.js only redraws at the new size once the element has actually been
   laid out, so the resize is deferred a frame. */
function resizeAllCharts(){
  requestAnimationFrame(() => {
    Object.values(CHARTS).forEach(c => { try{ c.resize(); }catch(e){} });
  });
}

function openFullScreen(card){
  if(FS_OPEN) return;
  const ov   = document.getElementById('fsov');
  const host = document.getElementById('fshost');
  const bar  = document.querySelector('.rangebar');

  /* A collapsed card would open as an empty box, so expand it first. */
  const body = card.querySelector('.cbody');
  if(body && body.classList.contains('shut')){
    body.classList.remove('shut');
    const t = card.querySelector('.ctog');
    if(t) t.textContent = '−';
  }

  /* The date range bar comes along so the window can be changed without
     collapsing back out. It is MOVED, not copied - two copies would drift
     out of sync the moment one of them was touched. */
  if(bar){
    moveInto(bar, ov);              /* marks where it came from */
    ov.insertBefore(bar, host);     /* then sit it above the chart */
  }
  moveInto(card, host);

  ov.classList.add('on');
  ov.setAttribute('aria-hidden', 'false');
  document.body.classList.add('fslock');
  FS_OPEN = card;
  resizeAllCharts();
}

function closeFullScreen(){
  if(!FS_OPEN) return;
  const ov  = document.getElementById('fsov');
  const bar = ov.querySelector('.rangebar');

  restoreMoved(FS_OPEN);
  if(bar) restoreMoved(bar);

  ov.classList.remove('on');
  ov.setAttribute('aria-hidden', 'true');
  document.body.classList.remove('fslock');
  FS_OPEN = null;
  resizeAllCharts();
}

/* Delegated, so it keeps working for cards that are rebuilt later (the Blood
   Pressure tab redraws itself whenever the date range changes). */
document.addEventListener('click', e => {
  const btn = e.target.closest('.cfs');
  if(btn){
    e.stopPropagation();          /* don't also fire the header's collapse */
    const card = btn.closest('.card');
    if(card) openFullScreen(card);
  }
});

document.getElementById('fsclose').addEventListener('click', closeFullScreen);

/* Escape closes it. The category popover also listens for Escape; whichever is
   open handles it, and closing both at once is harmless. */
document.addEventListener('keydown', e => {
  if(e.key === 'Escape') closeFullScreen();
});

/* Turning the phone sideways changes the available height. */
window.addEventListener('resize', () => { if(FS_OPEN) resizeAllCharts(); });

""" + ANCHOR

once(ANCHOR, NEW_FN, "behaviour")


# =============================================================================
# 5. Stop the header's collapse handler firing when the expand button is hit.
#    toggleCard reads head.nextElementSibling, so a click on the button would
#    otherwise collapse the card as it opens.
# =============================================================================
once("""function toggleCard(head){
  const body = head.nextElementSibling;""",
     """function toggleCard(head){
  /* The expand button sits inside the header, so a click on it also reaches
     this handler. window.event is the only way to see the original target from
     an inline onclick; bail out and let the expand handler deal with it. */
  const src = window.event && window.event.target;
  if(src && src.closest && src.closest('.cfs')) return;
  const body = head.nextElementSibling;""",
     "toggleCard guard")


io.open(P, "w", encoding="utf-8").write(s)
print("Patched index.html — %d -> %d bytes" % (before, len(s)))
