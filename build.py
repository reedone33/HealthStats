#!/usr/bin/env python3
# =============================================================================
# BUILD HEALTH.JSON  —  turns the big Apple Health CSV into a small data file
# =============================================================================
#
# WHY THIS EXISTS
# ---------------
# Apple Health exports one row per individual reading. That means the CSV is
# about 15 MB and roughly 287,000 rows long. A phone could technically download
# and read all of that every time you open the app, but it would be slow and
# would chew through mobile data.
#
# This script boils those 287,000 readings down to one summary per DAY — around
# 680 rows, roughly 300 KB. That is about fifty times smaller, and the app
# opens instantly.
#
# It uses only the tools that come with Python already. Nothing to install.
#
# HOW TO RUN IT
# -------------
# You normally won't run this by hand — double-clicking "update.command" runs
# it for you and then publishes the result. But if you want to run just this
# part, open Terminal in this folder and type:
#
#     python3 build.py
#
# It also ENCRYPTS the result. health.json is published to a public web
# address, so it is scrambled with your passphrase before it leaves this Mac.
# Anyone who fetches the file directly sees nothing but noise.
#
# INPUT :  Healthstats.csv   (the big export, stays on your Mac)
# OUTPUT:  health.json       (small, encrypted, safe to publish)
# =============================================================================

import base64
import csv
import getpass
import hashlib
import json
import os
import secrets
import sys
from collections import defaultdict
from datetime import datetime

# --- Where things live -------------------------------------------------------
# Everything is relative to the folder this script sits in, so it works no
# matter where the folder is moved to.
HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "Healthstats.csv")
JSON_PATH = os.path.join(HERE, "health.json")
PASS_PATH = os.path.join(HERE, ".passphrase")   # optional, never published

# --- Encryption settings -----------------------------------------------------
# health.json is published to a public web address, so it is encrypted before
# it leaves this Mac. Without the passphrase the file is meaningless noise.
#
# PBKDF2 turns your passphrase into a proper encryption key. The iteration count
# is deliberately high: it makes each guess slow, so someone trying millions of
# common passphrases against the file gets nowhere. 310,000 is the current
# OWASP recommendation for PBKDF2 with SHA-256.
PBKDF2_ITERATIONS = 310_000

# --- Which CSV column feeds which piece of the app ---------------------------
# The keys on the left are the exact column headings Apple writes out. The
# values on the right are the short names used inside the app. Short names keep
# health.json small, which keeps the app fast.
#
# If a future export renames or adds a column, this is the one place to change.
COLUMNS = {
    "Blood pressure (Systolic)(mmHg)":        "sys",
    "Blood pressure (Diastolic)(mmHg)":       "dia",
    "Heart rate(count/min)":                  "hr",
    "Resting heart rate(count/min)":          "rhr",
    "Walking heart rate average(count/min)":  "whr",
    "Time REM(hr)":                           "rem",
    "Time core(hr)":                          "core",
    "Time deep(hr)":                          "deep",
    "Time awake(hr)":                         "awake",
    "Time in bed(hr)":                        "bed",
    "Walking speed(mi/hr)":                   "spd",
    "Walking step length(in)":                "steplen",
    "Walking asymmetry percentage(%)":        "asym",
    "Walking double support percentage(%)":   "dbl",
    "Walking steadiness(%)":                  "stdy",
    "Respiratory Rate(count/min)":            "resp",
    "Oxygen saturation(%)":                   "o2",
    "VO2 Max(mL/min·kg)":                     "vo2",
    "Wrist temperature(degF)":                "temp",
}

# Sleep durations are the one group that must be ADDED UP across the day.
# You might have three separate sleep sessions in one night; the total time in
# deep sleep is all of them combined, not the average of them.
SUM_METRICS = {"rem", "core", "deep", "awake", "bed"}

# Everything else is a measurement taken at a moment in time — heart rate,
# walking speed, oxygen — so the sensible daily figure is the average.
# (Heart rate is special-cased further down to also give a low and a high.)


# =============================================================================
# ENCRYPTION
# =============================================================================
# The scheme, in plain terms:
#
#   1. A random "salt" is generated — 16 bytes that change every single build.
#      It stops anyone precomputing a dictionary of common passphrases.
#   2. Your passphrase plus that salt are stretched into a 256-bit key.
#   3. The data is encrypted with AES-256-GCM, the same cipher used for HTTPS.
#      GCM also stamps the result with a tag, so any tampering is detected
#      rather than silently decrypting to garbage.
#   4. Salt, nonce and ciphertext are written out together. The passphrase is
#      never written anywhere.
#
# The browser reverses exactly these steps using its own built-in crypto.

def load_cipher():
    """
    AES-GCM isn't in Python's standard library, so this uses the widely-used
    `cryptography` package. If it isn't installed, say so clearly rather than
    dying with a confusing traceback.
    """
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        return AESGCM
    except ImportError:
        print()
        print("  This build needs the 'cryptography' package, which isn't installed.")
        print("  Install it once by running this in Terminal:")
        print()
        print("      pip3 install cryptography")
        print()
        sys.exit(1)


def get_passphrase():
    """
    Where the passphrase comes from, in order of preference:

      1. A file called .passphrase in this folder, if you've made one. It's in
         .gitignore so it never reaches GitHub. Handy if you'd rather not type
         the passphrase on every update.
      2. Otherwise, ask for it here — twice on a first run, so a typo can't
         silently lock you out of your own data.
    """
    if os.path.exists(PASS_PATH):
        with open(PASS_PATH, encoding="utf-8") as f:
            phrase = f.read().strip()
        if phrase:
            print("  Using the passphrase from .passphrase")
            return phrase

    print()
    print("  Your data is encrypted before it's published.")
    print("  Enter the passphrase you use to open the app.")
    print("  (Nothing appears as you type — that's normal.)")
    print()

    while True:
        a = getpass.getpass("  Passphrase: ")
        if len(a) < 4:
            print("  Too short — use at least 4 characters.\n")
            continue
        b = getpass.getpass("  Again, to confirm: ")
        if a != b:
            print("  Those didn't match. Try again.\n")
            continue
        return a


def encrypt(plaintext_bytes, passphrase):
    """Return the encrypted envelope, ready to be written out as JSON."""
    AESGCM = load_cipher()

    salt = secrets.token_bytes(16)          # new every build
    nonce = secrets.token_bytes(12)         # must never repeat for a given key

    key = hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"),
                              salt, PBKDF2_ITERATIONS, dklen=32)

    ciphertext = AESGCM(key).encrypt(nonce, plaintext_bytes, None)

    b64 = lambda raw: base64.b64encode(raw).decode("ascii")
    return {
        "encrypted": True,
        "cipher": "AES-GCM",
        "kdf": "PBKDF2-SHA256",
        "iterations": PBKDF2_ITERATIONS,
        "salt": b64(salt),
        "nonce": b64(nonce),
        "data": b64(ciphertext),
    }


def parse_date(raw):
    """
    Pull a calendar date out of the CSV's Date column.

    The column holds one of two shapes:
        "2024-10-01 00:00:17"                         <- a single moment
        "2024-10-01 00:27:25 - 2024-10-01 06:22:25"   <- a span of time

    For spans we use the START, because a sleep session that begins at 11pm
    belongs to that night, not to the following morning.

    Returns a "YYYY-MM-DD" string, or None if the value can't be read.
    """
    if not raw:
        return None
    start = raw.split(" - ")[0].strip()
    # Take just the first 10 characters — "2024-10-01" — and check they look
    # like a date. This is far faster than full date parsing across 287k rows.
    day = start[:10]
    if len(day) == 10 and day[4] == "-" and day[7] == "-":
        return day
    return None


def to_float(raw):
    """
    Turn a CSV cell into a number, or None if it's blank or unreadable.
    Most cells in this export are blank — each row carries only one metric.
    """
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def main():
    # --- Check the input is actually there -----------------------------------
    if not os.path.exists(CSV_PATH):
        print("\n  Can't find Healthstats.csv in this folder.")
        print("  Export it from Apple Health and save it here, then try again.\n")
        sys.exit(1)

    size_mb = os.path.getsize(CSV_PATH) / (1024 * 1024)
    print(f"\n  Reading Healthstats.csv ({size_mb:.1f} MB)...")

    # --- Buckets to collect readings into ------------------------------------
    # "buckets" maps  day -> short metric name -> list of every reading that day.
    # defaultdict just means "create the empty slot automatically on first use",
    # which saves a lot of fiddly checking.
    buckets = defaultdict(lambda: defaultdict(list))

    # Blood pressure is kept as individual readings rather than daily averages.
    # There are only ~166 of them, and averaging two readings taken twelve hours
    # apart would hide exactly the variation worth looking at.
    bp_readings = []

    rows_read = 0
    rows_skipped = 0

    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        # Warn if the export's columns aren't what we expect, rather than
        # silently producing an app with empty charts.
        missing = [c for c in COLUMNS if c not in reader.fieldnames]
        if missing:
            print("\n  Heads up — these expected columns aren't in the CSV:")
            for c in missing:
                print(f"      {c}")
            print("  Their charts will be empty. Everything else still works.\n")

        for row in reader:
            rows_read += 1
            day = parse_date(row.get("Date"))
            if day is None:
                rows_skipped += 1
                continue

            # Blood pressure: systolic and diastolic arrive together on one row.
            # Only keep the pair when BOTH are present — a lone number is
            # meaningless as a blood pressure reading.
            s = to_float(row.get("Blood pressure (Systolic)(mmHg)"))
            d = to_float(row.get("Blood pressure (Diastolic)(mmHg)"))
            if s is not None and d is not None:
                bp_readings.append({"d": day, "s": round(s), "dia": round(d)})

            # Everything else: drop each non-blank reading into its day bucket.
            for column, short in COLUMNS.items():
                if short in ("sys", "dia"):
                    continue  # already handled above
                value = to_float(row.get(column))
                if value is not None:
                    buckets[day][short].append(value)

            # A progress line, because 287,000 rows takes a few seconds and
            # silence looks like a hang.
            if rows_read % 50000 == 0:
                print(f"      {rows_read:,} rows...")

    print(f"  Read {rows_read:,} rows.")

    # --- Collapse each day's readings into a single summary ------------------
    days = []
    for day in sorted(buckets.keys()):
        metrics = buckets[day]
        summary = {"d": day}

        for short, values in metrics.items():
            if not values:
                continue
            if short in SUM_METRICS:
                # Sleep stages add up across the night's sessions.
                summary[short] = round(sum(values), 3)
            else:
                # Everything else averages.
                summary[short] = round(sum(values) / len(values), 2)

        # Heart rate gets the full picture: lowest, average and highest of the
        # day. That range is the interesting bit, and there are enough readings
        # (hundreds per day) for it to be meaningful.
        hr_values = metrics.get("hr")
        if hr_values:
            summary["hrLo"] = round(min(hr_values))
            summary["hr"] = round(sum(hr_values) / len(hr_values))
            summary["hrHi"] = round(max(hr_values))
            summary["hrN"] = len(hr_values)

        # Total sleep. The export's own "Time asleep" column is almost entirely
        # blank (7 values out of 287,000), so it can't be trusted. Adding the
        # three stages together gives the same number and is always available.
        stages = [summary.get(k, 0) for k in ("rem", "core", "deep")]
        if any(stages):
            summary["asleep"] = round(sum(stages), 3)

        days.append(summary)

    # --- Sanity filter -------------------------------------------------------
    # On some nights the "Time in bed" figure is clearly incomplete: the watch
    # records six hours of sleep stages but only ten minutes in bed. The stage
    # data on those nights is fine — it's the in-bed total that didn't get
    # written properly, usually because the session was logged in pieces.
    #
    # So rather than throw the whole night away, we just remove the untrustworthy
    # "bed" figure and keep the sleep stages. The Time-in-Bed chart will have a
    # gap for that night; every other sleep chart is unaffected.
    #
    # This is also why the app works out stage percentages as a share of TOTAL
    # SLEEP rather than of time in bed: total sleep is recorded reliably on every
    # night, so the percentages are comparable all the way across the range.
    cleaned = 0
    for day in days:
        bed = day.get("bed")
        asleep = day.get("asleep")
        if bed and asleep and asleep > bed * 1.02:  # 2% tolerance for rounding
            day.pop("bed", None)
            cleaned += 1

    # --- Write the result ----------------------------------------------------
    payload = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "Apple Health export",
        "rowsRead": rows_read,
        "days": days,
        "bp": bp_readings,
    }

    # separators=(",", ":") strips the spaces JSON normally puts after commas
    # and colons. Invisible to the app, and it shaves a good chunk off the size.
    plaintext = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    plain_kb = len(plaintext) / 1024

    # Encrypt before writing. Nothing readable ever touches the disk here, so
    # there's no window where a plain copy could be committed by accident.
    envelope = encrypt(plaintext, get_passphrase())
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(envelope, f, separators=(",", ":"))

    out_kb = os.path.getsize(JSON_PATH) / 1024

    # --- Tell the user what happened ----------------------------------------
    print()
    print(f"  Wrote health.json — {out_kb:.0f} KB, encrypted (AES-256-GCM)")
    print(f"      {plain_kb:.0f} KB of data, unreadable without the passphrase")
    print(f"      {len(days):,} days   {days[0]['d']} to {days[-1]['d']}")
    print(f"      {len(bp_readings):,} blood pressure readings")
    if rows_skipped:
        print(f"      {rows_skipped:,} rows had an unreadable date and were skipped")
    if cleaned:
        print(f"      {cleaned} night(s) had an incomplete 'time in bed' figure — that one value dropped, sleep stages kept")
    print(f"      {size_mb:.1f} MB in, {out_kb / 1024:.2f} MB out")
    print()


if __name__ == "__main__":
    main()
