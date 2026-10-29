#!/usr/bin/env bash
# Download the Open Duck Mini files the walking simulation needs, at the commits this project was tested with.
#   Open_Duck_Playground - the MuJoCo model the walking policy was trained on (no licence file in that repo,
#                          so it is downloaded here rather than copied into this project)
#   Open_Duck_Mini       - only the robot's full-detail 3D parts (Apache 2.0)
# Usage: third_party/fetch_open_duck.sh
set -euo pipefail
dest="$(cd "$(dirname "$0")" && pwd)/open_duck/src"
mkdir -p "$dest"
if [ ! -d "$dest/Open_Duck_Playground/.git" ]; then
  git clone https://github.com/apirrone/Open_Duck_Playground.git "$dest/Open_Duck_Playground"
fi
git -C "$dest/Open_Duck_Playground" checkout --quiet b9be205ac64488c23504ca42e5ec790337adeec3
if [ ! -d "$dest/Open_Duck_Mini/.git" ]; then
  git clone --filter=blob:none --no-checkout https://github.com/apirrone/Open_Duck_Mini.git "$dest/Open_Duck_Mini"
  git -C "$dest/Open_Duck_Mini" sparse-checkout set mini_bdx/robots/open_duck_mini_v2
fi
git -C "$dest/Open_Duck_Mini" checkout --quiet b23317a485b3cec7d8417f352478778b3475173c
echo "Open Duck files ready in $dest"
