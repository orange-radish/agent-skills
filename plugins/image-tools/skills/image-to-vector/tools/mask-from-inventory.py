#!/usr/bin/env python3
"""mask-from-inventory.py — binarise a raster with the inventory's own rule.

Use when `vtracer --colormode bw` fails to separate the subject from the
background. vtracer binarises on luminance, which works for a light subject
on a dark field but not for a mid-brightness one: a mid-green ball on navy
comes back as nothing at all — vtracer emits only the background rectangle
and silently drops the subject. Colour mode is not the answer either; it
produces a separate path per antialiasing shade (dozens for a flat
two-colour icon).

inspect-outline.py already solved this. It records the threshold it used in
`image.outline_source`, e.g.

    "color-distance > 105 (bg=#001020)"

This script reproduces exactly that threshold and writes a black-on-white
mask. Tracing the mask instead of the raster has a second benefit beyond
getting a usable trace at all: vtracer and the inventory then describe the
*same* mask, so their contours correspond and the segment plan lines up.

The mask is a means of measuring the source, not an output — the source
raster is still the visual source of truth (`criteria/visual-fidelity.md`),
and coordinates remain traceable through vtracer's path commands.

Polarity is subject=black on white=background, matching what vtracer's bw
mode produces for a light-on-dark source: the traced subject regions come
back as subpaths you keep.

Usage:
  python3 mask-from-inventory.py INVENTORY.json SOURCE.png OUT-MASK.png

Then trace the mask, not the original:
  vtracer --input OUT-MASK.png --output trace.svg --colormode bw --mode spline

Requires: Pillow + NumPy (see tools/requirements.txt). Python >= 3.10.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.strip().splitlines()[-6], file=sys.stderr)
        print("usage: mask-from-inventory.py INVENTORY.json SOURCE.png OUT.png",
              file=sys.stderr)
        return 2
    inv_path, src_path, out_path = argv

    inv = json.loads(Path(inv_path).read_text())
    rule = inv.get("image", {}).get("outline_source", "")
    m = re.match(r"color-distance > ([\d.]+) \(bg=#([0-9A-Fa-f]{6})\)", rule)
    if not m:
        print(f"unrecognised image.outline_source: {rule!r}\n"
              f"(expected inspect-outline.py's 'color-distance > N (bg=#RRGGBB)')",
              file=sys.stderr)
        return 1
    thresh = float(m.group(1))
    bg = np.array([int(m.group(2)[i:i + 2], 16) for i in (0, 2, 4)], float)

    rgb = np.asarray(Image.open(src_path).convert("RGB"), float)
    subject = np.sqrt(((rgb - bg) ** 2).sum(2)) > thresh

    Image.fromarray(np.where(subject, 0, 255).astype(np.uint8)).save(out_path)

    frac = 100.0 * subject.mean()
    print(f"rule: {rule}")
    print(f"subject: {int(subject.sum())} px of {subject.size} ({frac:.1f}%) "
          f"-> {out_path}")
    if frac < 0.5 or frac > 99.5:
        print("WARNING: the mask is nearly empty or nearly full — check that "
              "the inventory came from this same source raster.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
