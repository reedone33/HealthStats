#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Gives the "All readings" table the same full-screen button the charts have.
#
# The overlay machinery already moves whole CARD elements, so it needs no
# changes - the table only needs the button and a little CSS so it actually
# uses the extra height instead of keeping its 340px scroll box.
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
# 1. THE BUTTON
# =============================================================================
once("""        <div><div class="ctitle">All readings</div>
        <div class="csub">newest first</div></div>
        <button class="ctog">−</button>""",
     """        <div><div class="ctitle">All readings</div>
        <div class="csub">newest first</div></div>
        <div class="cbtns">
          <button class="cfs" title="Full screen" aria-label="Full screen">&#9974;</button>
          <button class="ctog">−</button>
        </div>""",
     "button")


# =============================================================================
# 2. LET THE TABLE GROW WHEN IT IS FULL SCREEN
#    In the grid the table lives in a 340px scroll box. Full screen, it should
#    take the height that is going spare, exactly as a chart does.
# =============================================================================
once("/* Stop the page behind from scrolling while the overlay is open. */",
     """/* A table expanded to full screen drops its 340px cap and takes the height
   that is going spare, the same way a chart does. min-height:0 is what lets a
   flex child actually shrink its scroll box rather than overflowing the panel. */
#fshost .tblwrap{max-height:none !important;flex:1 1 auto;min-height:0;}

/* With 200+ rows on screen the column headings have to stay put, or you lose
   track of which number is which halfway down. */
#fshost .tblwrap thead th{
  position:sticky;top:0;z-index:1;
  background:var(--card);
  box-shadow:0 1px 0 var(--bdr);
}

/* Stop the page behind from scrolling while the overlay is open. */""",
     "css")


io.open(P, "w", encoding="utf-8").write(s)
print("Patched index.html — %d -> %d bytes" % (before, len(s)))
