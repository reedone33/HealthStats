#!/bin/bash
# =============================================================================
# UPDATE AND PUBLISH THE HEALTH STATS APP
# =============================================================================
# Double-click this file in Finder. It does three things in order:
#
#     1. Rebuilds health.json from your latest Healthstats.csv
#     2. Bumps the version number so installed copies know to update
#     3. Sends everything to GitHub, which publishes the live site
#
# It uses whatever GitHub sign-in is already set up on your Mac — GitHub
# Desktop counts. Nothing here asks for, stores or handles a password.
#
# Your normal routine becomes:
#     export from Apple Health  ->  save over Healthstats.csv  ->  double-click this
# =============================================================================

cd "$(dirname "$0")" || exit 1

echo ""
echo "  Health Stats — update and publish"
echo "  ================================="
echo ""

# --- Step 0: is everything we need actually here? ----------------------------
if ! command -v python3 >/dev/null 2>&1; then
  echo "  Python isn't installed on this Mac."
  echo "  Open Terminal and run:  xcode-select --install"
  echo ""
  read -n 1 -s -r -p "  Press any key to close."
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "  git isn't installed on this Mac."
  echo "  Open Terminal and run:  xcode-select --install"
  echo ""
  read -n 1 -s -r -p "  Press any key to close."
  exit 1
fi

if [ ! -f Healthstats.csv ]; then
  echo "  Healthstats.csv isn't in this folder."
  echo "  Export from Apple Health, save it here with that exact name, and try again."
  echo ""
  read -n 1 -s -r -p "  Press any key to close."
  exit 1
fi

# --- Step 1: rebuild the data file -------------------------------------------
echo "  [1/3] Rebuilding health.json from your CSV"
echo ""
if ! python3 build.py; then
  echo ""
  echo "  The rebuild failed, so nothing was published."
  echo "  The message above should say why."
  echo ""
  read -n 1 -s -r -p "  Press any key to close."
  exit 1
fi

# --- Step 2: bump the cache version ------------------------------------------
# The service worker only lets go of its saved copy when this name changes.
# Without this step you'd publish new data and your phone would keep showing
# the old numbers. We use the date and time, so it's always different.
STAMP=$(date '+%Y%m%d-%H%M')
echo "  [2/3] Setting cache version to health-$STAMP"

# sed edits the file in place. The '' after -i is required on macOS.
sed -i '' -E "s/const CACHE_VERSION = '[^']*';/const CACHE_VERSION = 'health-$STAMP';/" sw.js

if ! grep -q "health-$STAMP" sw.js; then
  echo ""
  echo "  Couldn't update the version line in sw.js. Nothing was published."
  echo "  Check that sw.js still has a line starting: const CACHE_VERSION ="
  echo ""
  read -n 1 -s -r -p "  Press any key to close."
  exit 1
fi

# --- Step 3: send it to GitHub ------------------------------------------------
echo "  [3/3] Publishing to GitHub"
echo ""

if [ ! -d .git ]; then
  echo "  This folder isn't connected to a GitHub repository."
  echo "  Open GitHub Desktop and add it as a local repository first."
  echo ""
  read -n 1 -s -r -p "  Press any key to close."
  exit 1
fi

if [ -z "$(git status --porcelain)" ]; then
  echo "  Nothing has changed since the last publish."
  echo ""
  read -n 1 -s -r -p "  Press any key to close."
  exit 0
fi

echo "  These files will be sent:"
echo ""
git status --short | sed 's/^/    /'
echo ""
echo "  (Healthstats.csv is deliberately excluded — it's 15 MB and the app"
echo "   doesn't need it. It stays on this Mac.)"
echo ""

read -r -p "  Publish? [y/N] " REPLY
echo ""
case "$REPLY" in
  [yY]) ;;
  *) echo "  Cancelled — nothing was sent."
     echo ""
     read -n 1 -s -r -p "  Press any key to close."
     exit 0 ;;
esac

git add -A
git commit -m "Update health data — $(date '+%d %b %Y %H:%M')" || {
  echo "  Commit failed. Nothing was sent."
  echo ""
  read -n 1 -s -r -p "  Press any key to close."
  exit 1
}

echo ""
echo "  Sending..."
if git push; then
  echo ""
  echo "  Published. The live site updates within a minute or two."
  echo "  On your phone, close the app fully and reopen it to pick up the new data."
else
  echo ""
  echo "  The push was refused. Usually that means this Mac isn't signed in to"
  echo "  GitHub yet. Open GitHub Desktop, sign in, add this folder as a local"
  echo "  repository, then try again."
fi

echo ""
read -n 1 -s -r -p "  Press any key to close."
