#!/usr/bin/env bash
# Download Pollen Robotics' open-source repos at the commits this project was tested with.
#   AmazingHand  - humanoid hand: CAD/STL print files, firmware examples, hand-tracking demo
#   reachy_mini  - Reachy Mini SDK, MuJoCo simulation and the conversation (talking) app
# Usage: third_party/fetch_pollen.sh
set -euo pipefail
dest="$(cd "$(dirname "$0")" && pwd)/pollen/src"
mkdir -p "$dest"
fetch() {  # name commit
  if [ ! -d "$dest/$1/.git" ]; then git clone "https://github.com/pollen-robotics/$1.git" "$dest/$1"; fi
  git -C "$dest/$1" fetch --quiet origin "$2" || true
  git -C "$dest/$1" checkout --quiet "$2"
  echo "$1 at $(git -C "$dest/$1" rev-parse --short HEAD) in $dest/$1"
}
fetch AmazingHand 3e8241074df3436a3044ced4881e3bb2133aa725
fetch reachy_mini 5feff22cbe9614709b8131f3de4209d0ac24452c
echo "Print files: $dest/AmazingHand/cad/stl"
