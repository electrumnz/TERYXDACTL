#!/usr/bin/env bash
# Render every printable part to cad/stl/. Needs OpenSCAD (2021.01 or newer).
#   ./cad/build.sh            all parts
#   ./cad/build.sh pi_box     just the files whose name starts with pi_box
set -euo pipefail
cd "$(dirname "$0")"
OPENSCAD=${OPENSCAD:-openscad}
only=${1:-}
mkdir -p stl

info=$("$OPENSCAD" -o /tmp/teryx_split.echo split_check.scad 2>&1 && cat /tmp/teryx_split.echo)
echo "$info" | grep -E 'SPLIT|SIZE' | sed 's/ECHO: //; s/"//g'
split() { echo "$info" | grep -q "$1=true"; }

jobs=()
add() { jobs+=("$1|$2|$3"); }   # out name | scad file | part

if split frame; then add dash_panel_left dash_panel part=left;  add dash_panel_right dash_panel part=right
else add dash_panel dash_panel part=whole; fi
if split plate; then add back_plate_left back_plate part=left; add back_plate_right back_plate part=right
else add back_plate back_plate part=whole; fi
if split hood; then add sun_hood_left sun_hood part=left; add sun_hood_right sun_hood part=right; add sun_hood_splice sun_hood part=splice
else add sun_hood sun_hood part=whole; fi
for p in box lid gasket; do add "pi_box_$p" pi_box "part=$p"; done
for b in control_box relay_box; do for p in box lid gasket plate; do add "${b}_$p" "$b" "part=$p"; done; done
add fit_test_corner fit_test part=none
add speaker_pod speaker_pod part=pod
add speaker_pod_cover speaker_pod part=cover
add speaker_pod_plug speaker_pod part=plug
for p in head head_teeth head_eyes head_pupils jaw jaw_teeth; do add "speaker_pod_$p" speaker_pod "part=$p"; done
add speaker_pod_gasket speaker_pod part=gasket

rm -f stl/*.stl.tmp
for j in "${jobs[@]}"; do
  IFS='|' read -r out file part <<<"$j"
  [[ -n "$only" && "$out" != "$only"* ]] && continue
  echo "-> stl/$out.stl"
  rm -f "stl/$out.stl"
  "$OPENSCAD" --quiet --hardwarnings -o "stl/$out.stl" -D "${part%%=*}=\"${part#*=}\"" "parts/$file.scad"
  # an empty or broken render must fail the build
  [[ $(grep -c facet "stl/$out.stl") -gt 10 ]] || { echo "empty STL: $out" >&2; exit 1; }
  python3 stl_to_binary.py "stl/$out.stl"
done
if [[ -z "$only" || "back_plate_dxf" == "$only"* ]]; then
  echo "-> stl/back_plate.dxf"
  "$OPENSCAD" --quiet --hardwarnings -o stl/back_plate.dxf parts/back_plate_2d.scad
fi
if [[ -z "$only" || "pi_lid_dxf" == "$only"* || "pi_box" == "$only"* ]]; then
  echo "-> stl/pi_lid_plate.dxf"
  "$OPENSCAD" --quiet --hardwarnings -o stl/pi_lid_plate.dxf parts/pi_lid_2d.scad
fi
if [[ -z "$only" || "speaker_pod" == "$only"* ]]; then
  # The pod's air volume must match config/speaker_pods.yaml (the bass maths uses it)
  echo "-> speaker pod air volume"
  "$OPENSCAD" --quiet --hardwarnings -o /tmp/teryx_pod_cavity.stl -D 'part="cavity"' parts/speaker_pod.scad
  want=$(sed -n 's/^ *gross_l: *\([0-9.]*\).*/\1/p' ../config/speaker_pods.yaml)
  python3 stl_volume.py /tmp/teryx_pod_cavity.stl "$want"
fi
echo "Done."
