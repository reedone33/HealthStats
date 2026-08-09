# Health Stats

An installable web app for Apple Health data — sleep, blood pressure, heart rate,
walking and vitals. Personal project, not medical software.

---

## What's in this folder

| File | What it does |
|---|---|
| `index.html` | The app itself — layout, charts and behaviour |
| `health.json` | The data the app reads. Small, built from the CSV, **encrypted** |
| `Healthstats.csv` | Your raw Apple Health export. **Stays on this Mac** |
| `build.py` | Turns the big CSV into the small `health.json` |
| `update.command` | Double-click to rebuild and publish in one go |
| `sw.js` | Makes the app installable and able to open offline |
| `manifest.webmanifest`, `icons/` | Home screen name and icon |
| `.gitignore` | Keeps the CSV and your passphrase out of GitHub |
| `.nojekyll` | Stops GitHub treating the site as a blog. Leave it |

---

## First-time setup

You do this once. After that, updating is a double-click.

### 1. Install the encryption library

Your data is encrypted before it's published. That needs one Python package,
installed once. In Terminal:

```
pip3 install cryptography
```

### 2. Choose your passphrase

There's no passphrase stored anywhere for the app to check against. You pick one
when you run `update.command`, and it becomes the key that actually encrypts the
file. Type it into the app to decrypt.

This means two things worth being clear about:

- **Anyone fetching `health.json` from the public web address gets noise.** Not
  a login page they might bypass — genuinely unreadable data. That's the point.
- **If you forget the passphrase, the published data is gone.** There's no
  recovery, by design. You'd rebuild from `Healthstats.csv`, which is why that
  file stays safe on your Mac.

Use something you'll remember. It can be any length and any characters.

*Optional:* if you'd rather not type it on every update, create a file called
`.passphrase` in this folder containing just the passphrase. It's in
`.gitignore` so it never reaches GitHub — **but note this folder syncs to
OneDrive**, so the passphrase would sync to Microsoft's servers too. Typing it
each time avoids that.

### 3. Publish it

1. Open **GitHub Desktop**. This folder should already appear as the
   `HealthStats` repository.
2. You'll see a list of changed files down the left. Type a summary like
   `First version` in the box at the bottom left.
3. Click **Commit to main**, then **Push origin** at the top.

### 4. Turn on GitHub Pages

1. In GitHub Desktop: **Repository → View on GitHub**. Your browser opens.
2. Click **Settings** (across the top of the repository page).
3. Click **Pages** in the left sidebar.
4. Under **Source**, choose **Deploy from a branch**.
5. Set the branch to **main** and the folder to **/ (root)**. Click **Save**.
6. Wait a minute or two and refresh. GitHub shows your address near the top:

   ```
   https://reedone33.github.io/HealthStats/
   ```

### 5. Put it on your iPhone

Open that address in **Safari** — on iOS only Safari can install web apps,
Chrome can't. Tap the **Share** button, scroll down, tap **Add to Home Screen**.

It gets an icon and opens full-screen with no browser chrome, like any other app.

> **Why publish at all, rather than just opening the file?** Two reasons.
> Service workers — the thing that makes an app installable and able to work
> offline — only run over `https`. And browsers refuse to let a page opened from
> your hard drive load a separate data file, so `health.json` wouldn't load and
> the app would show an error.

---

## Updating with new data

1. Export from Apple Health and save it over `Healthstats.csv` in this folder,
   keeping that exact filename.
2. Double-click **`update.command`**.
3. Type your passphrase when asked. Nothing appears as you type — that's normal.
4. Press `y` to publish.

That's it. The script rebuilds `health.json`, encrypts it, bumps the version so
your phone knows to fetch the new data, and pushes to GitHub. The live site
updates within a minute or two.

**Use the same passphrase every time**, unless you deliberately want to change
it. If you change it, every device will ask for the new one on next open.

On your phone, close the app fully (swipe it away from the app switcher) and
reopen it to pick up the new numbers.

---

## How the data is handled

The raw export has around 287,000 rows, because Apple writes one row per
individual reading. `build.py` collapses that into one summary per day — about
680 rows and 140 KB, roughly fifty times smaller. That's the difference between
an app that opens instantly and one that downloads 15 MB over cellular every
time you glance at it.

A few decisions worth knowing about, since they affect what you see:

**Sleep percentages are a share of total sleep, not of time in bed.** The
"time in bed" figure is missing or clearly incomplete on around 99 nights —
one night records six hours of sleep stages but only ten minutes in bed. Total
sleep is recorded reliably every night, so using it as the denominator keeps the
percentages comparable across the whole range. On those 99 nights the Time in
Bed chart shows a gap; every other sleep chart is unaffected.

**Total sleep is REM + Core + Deep added together.** The export's own
"Time asleep" column has 7 values out of 287,000 rows, so it can't be used.

**Blood pressure is kept as individual readings, not daily averages.** There are
only 166 of them, and averaging a morning and an evening reading would hide
exactly the variation worth looking at.

**Heart rate gets a low, average and high for each day** — there are enough
readings (usually several hundred a day) for that range to mean something.

**Sparse metrics.** Blood oxygen, VO₂ max, walking steadiness and wrist
temperature are recorded on only a few dozen days each. Those charts will look
thin. They're not broken; there just isn't much data yet.

---

## If something goes wrong

**"Couldn't load your data" when you open the app.** Almost always because the
file was opened from Finder rather than from the published web address.

**The app shows old numbers after publishing.** Close it fully from the app
switcher and reopen. If it persists, check that `update.command` reported a new
cache version.

**`update.command` won't open — macOS says it's from an unidentified developer.**
Right-click it, choose **Open**, then **Open** again in the dialog. You only
need to do this the first time.

**"That passphrase didn't work."** Either a typo, or the file was built with a
different passphrase than the one you're typing. Rebuild with `update.command`
using the passphrase you want and try again.

**You forgot the passphrase.** The published data can't be recovered — that's
what makes the encryption worth anything. Run `update.command`, set a new
passphrase, and it rebuilds from `Healthstats.csv`.

---

## How the encryption works

`build.py` takes your passphrase and runs it through PBKDF2-SHA256 with 310,000
iterations and a fresh random salt, producing a 256-bit key. The data is then
encrypted with AES-256-GCM — the same cipher that protects HTTPS connections.
Only the salt, the nonce and the ciphertext are published. The passphrase itself
is never written anywhere.

The app reverses this in your browser using the built-in Web Crypto API. GCM
carries an integrity tag, so a wrong passphrase or a tampered file fails
outright rather than quietly producing nonsense.

The high iteration count means unlocking takes a moment — a fraction of a second
on a phone. That delay is deliberate: it's what makes guessing passphrases at
scale impractical.

### The honest limits

**A weak passphrase is a weak lock.** The encryption is only as good as what you
choose. `1234` would fall to a determined attacker; a memorable phrase of several
words would not.

**"Remember on this device" stores the passphrase in that browser.** Convenient,
and reasonable on your own phone. Untick it on anything shared.

**Your earlier unencrypted data is still in the repository's history.** Every
version you commit is kept by git forever, and the first few commits contained
`health.json` in plain text on a public repository. Encrypting from now on
doesn't retroactively hide those. If that matters to you, the fix is to wipe the
history and start fresh — ask Claude to do it, or make the repository private
(which needs GitHub Pro for Pages to keep working).
