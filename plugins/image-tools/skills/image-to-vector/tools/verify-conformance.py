#!/usr/bin/env python3
"""verify-conformance.py — inventory conformance check for image-to-vector.

Mechanically enforces the inventory-conformance rules that
`criteria/geometry.md` states in prose. Eyeballing zoom crops reliably
catches a collapsed region; it does not reliably catch a corner rounded by
a few pixels, and it cannot check every vertex on every contour.

Checks each structural vertex in the inventory against the authored path:

  1. missing node   — a `corner`/`sharp_corner`/`spike` vertex with no
                      authored path node within --tol px of it.
  2. missing kink / — a node is there, but the authored path bends through
     smoothed spike   far less angle than the inventory measured, i.e. the
                      curve runs smoothly through what should be a corner.
  3. phantom notch  — the authored path bends at least --phantom degrees
                      where the inventory has no structural vertex (a kink
                      invented during tracing).

How the angle is measured, and why it matters:

  The authored turn is a CHORD angle measured on the SAME BASELINE the
  inventory used — out to the neighbouring inventory vertices, walking
  along the flattened curve. Two cheaper metrics are both wrong here:

    * Control-point tangents. A cusp with short control arms is genuinely
      sharp on screen while its tangents barely diverge, so a tangent test
      reports a perfectly good spike tip as smoothed.
    * A fixed short probe. The inventory's `turn_deg` spans neighbouring
      RDP vertices, which may be hundreds of px apart, and that angle
      absorbs the curvature of the arcs either side. Measuring the authored
      path over 8 px and comparing it to that inflated number reports every
      corner between two curved segments as smoothed.

  Phantom-notch detection has no inventory vertex to take a baseline from,
  so it uses the fixed --probe window.

Thresholds (defaults; the vertex-kind angle bands live in
inspect-outline.py's docstring and are not restated here):

  --tol          4.0   px, node-coincidence radius
  --turn-frac    0.5   authored turn must reach this fraction of the
                       inventory's turn_deg ...
  --turn-floor  20.0   ... unless it already exceeds this many degrees
  --phantom     45.0   deg, authored turn that must be explained by a vertex
  --probe        8.0   px, baseline for phantom-notch detection only
  --min-baseline 6.0   px, below which a vertex's kink is left unchecked
                       rather than measured from a degenerate chord

A shallow corner (30-45 deg) reported just under threshold is usually
cosmetic. The tool reports; you decide, after looking at the zoom crop.

Usage:
  python3 verify-conformance.py INVENTORY.json --svg AUTHORED.svg
  python3 verify-conformance.py INVENTORY.json --nodes NODES.json [--normalized]

`--svg` reads every subpath of every <path>; the SVG must be in the same
coordinate space as the raster the inventory came from. `--nodes` takes a
JSON list of subpaths, for outputs that are not SVG (SwiftUI, Compose,
VectorDrawable) — each a flat list in the same order an SVG path uses:

  [[x0, y0,  c1x, c1y, c2x, c2y, x1, y1,  ...], ...]

Add --normalized when those numbers are 0..1; they are scaled onto the
inventory's bounding box first, so --tol and --probe stay in source px.

Exit status is 1 if any check fails, so this can gate a build.
Requires: NumPy (see tools/requirements.txt). Python >= 3.10.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

STRUCTURAL = ("corner", "sharp_corner", "spike")
SAMPLES_PER_CUBIC = 24


# ---------------------------------------------------------------------------
# Reading authored paths
# ---------------------------------------------------------------------------

def subpaths_from_svg(text: str) -> list[tuple[list[float], bool]]:
    """Flatten every <path d="..."> into (number run, closed) pairs.

    M, C, L and Z are handled — vtracer emits cubics exclusively, and L is
    expanded to a degenerate cubic so straight joins still measure.

    Closure comes from the `Z` command, not from comparing endpoints:
    vtracer closes with `Z` while leaving the final point a fraction of a
    pixel off the start, so an endpoint-equality test misreports those
    subpaths as open and leaves their start node unmeasurable.
    """
    out: list[tuple[list[float], bool]] = []
    for d in re.findall(r'<path[^>]*\sd="([^"]+)"', text, re.S):
        for chunk in re.split(r"(?=[Mm])", d):
            chunk = chunk.strip()
            if not chunk or chunk[0] not in "Mm":
                continue
            nums: list[float] = []
            cur = None
            closed = False
            for cmd, body in re.findall(r"([MmCcLlZz])([^MmCcLlZz]*)", chunk):
                vals = [float(v) for v in
                        re.findall(r"-?\d*\.?\d+(?:[eE][-+]?\d+)?", body)]
                if cmd in "Mm":
                    cur = (vals[0], vals[1])
                    nums += [cur[0], cur[1]]
                elif cmd in "Cc":
                    for i in range(0, len(vals) - 5, 6):
                        seg = vals[i:i + 6]
                        nums += seg
                        cur = (seg[4], seg[5])
                elif cmd in "Ll":
                    for i in range(0, len(vals) - 1, 2):
                        x, y = vals[i], vals[i + 1]
                        nums += [cur[0], cur[1], x, y, x, y]
                        cur = (x, y)
                elif cmd in "Zz":
                    closed = True
            if len(nums) >= 8:
                out.append((nums, closed))
    return out


class Flat:
    """A subpath flattened to a polyline, with its on-curve nodes located."""

    def __init__(self, sub: list[float], closed: bool):
        start = np.array(sub[0:2], float)
        cubics = []
        cur = start
        for i in range(2, len(sub) - 5, 6):
            cubics.append((cur,
                           np.array(sub[i:i + 2], float),
                           np.array(sub[i + 2:i + 4], float),
                           np.array(sub[i + 4:i + 6], float)))
            cur = cubics[-1][3]

        poly: list[np.ndarray] = []
        node_at: list[int] = []
        for (p0, c1, c2, p3) in cubics:
            node_at.append(len(poly))
            for j in range(SAMPLES_PER_CUBIC):
                t = j / SAMPLES_PER_CUBIC
                mt = 1 - t
                poly.append(mt**3 * p0 + 3 * mt**2 * t * c1
                            + 3 * mt * t**2 * c2 + t**3 * p3)
        poly.append(cubics[-1][3])

        self.P = np.array(poly)
        seg = np.sqrt(((self.P[1:] - self.P[:-1]) ** 2).sum(1))
        self.s = np.concatenate([[0.0], np.cumsum(seg)])
        self.total = float(self.s[-1])
        self.closed = closed and np.hypot(*(cubics[-1][3] - start)) <= 1.0
        self.node_idx = list(node_at) if self.closed else list(node_at) + [len(self.P) - 1]
        self.nodes = self.P[self.node_idx]

    def _at(self, target: float) -> np.ndarray | None:
        if self.closed and self.total > 0:
            target %= self.total
        elif target < 0 or target > self.total:
            return None
        return self.P[min(int(np.searchsorted(self.s, target, side="left")),
                          len(self.P) - 1)]

    def turn_at(self, k: int, back: float, fwd: float) -> float | None:
        """Chord angle at node k, measured `back` px behind and `fwd` ahead."""
        i = self.node_idx[k]
        a, b = self._at(self.s[i] - back), self._at(self.s[i] + fwd)
        if a is None or b is None:
            return None
        inc, out = self.P[i] - a, b - self.P[i]
        na, nb = np.hypot(*inc), np.hypot(*out)
        if na < 1e-9 or nb < 1e-9:
            return None
        cos = float(np.dot(inc, out) / (na * nb))
        return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("inventory")
    ap.add_argument("--svg")
    ap.add_argument("--nodes")
    ap.add_argument("--normalized", action="store_true")
    ap.add_argument("--tol", type=float, default=4.0)
    ap.add_argument("--turn-frac", type=float, default=0.5)
    ap.add_argument("--turn-floor", type=float, default=20.0)
    ap.add_argument("--phantom", type=float, default=45.0)
    ap.add_argument("--probe", type=float, default=8.0)
    ap.add_argument("--min-baseline", type=float, default=6.0)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    if bool(args.svg) == bool(args.nodes):
        ap.error("pass exactly one of --svg or --nodes")

    inv = json.loads(Path(args.inventory).read_text())
    if args.svg:
        subs = subpaths_from_svg(Path(args.svg).read_text())
    else:
        subs = [(s, True) for s in json.loads(Path(args.nodes).read_text())]
    if not subs:
        print("FAIL: no authored subpaths found", file=sys.stderr)
        return 1

    verts = [(ci, vi, v)
             for ci, c in enumerate(inv["contours"])
             for vi, v in enumerate(c["vertices"])]
    inv_xy = np.array([v["xy"] for _, _, v in verts], float)

    if args.normalized:
        lo, hi = inv_xy.min(0), inv_xy.max(0)
        span = hi - lo
        subs = [([lo[i % 2] + v * span[i % 2] for i, v in enumerate(nums)], cl)
                for nums, cl in subs]

    flats = [Flat(nums, cl) for nums, cl in subs]
    # (flat index, node index) for every authored node, and their positions
    owner = [(fi, k) for fi, f in enumerate(flats) for k in range(len(f.nodes))]
    all_nodes = np.vstack([f.nodes for f in flats])

    failures: list[str] = []
    unchecked: list[str] = []
    matched: set[int] = set()

    for (ci, vi, v) in verts:
        if v["kind"] not in STRUCTURAL:
            continue
        q = np.array(v["xy"], float)
        dist = np.sqrt(((all_nodes - q) ** 2).sum(1))
        g = int(np.argmin(dist))
        if dist[g] > args.tol:
            failures.append(
                f"missing node: contour {ci} v{vi} ({v['kind']}, turn "
                f"{v['turn_deg']:.0f}deg) at ({q[0]:.1f},{q[1]:.1f}) — nearest "
                f"authored node is {dist[g]:.1f}px away (tol {args.tol})")
            continue
        matched.add(g)

        # Baseline: the neighbouring inventory vertices, which is what the
        # inventory's own turn_deg was measured against.
        cverts = inv["contours"][ci]["vertices"]
        prev_xy = np.array(cverts[(vi - 1) % len(cverts)]["xy"], float)
        next_xy = np.array(cverts[(vi + 1) % len(cverts)]["xy"], float)
        back = float(np.hypot(*(q - prev_xy)))
        fwd = float(np.hypot(*(next_xy - q)))
        if min(back, fwd) < args.min_baseline:
            # Adjacent structural vertices this close (a tight double-corner)
            # leave too short a chord to measure an angle from. Lengthening
            # the chord would reach past the neighbour and measure a
            # different feature, so report it as unchecked rather than
            # guessing.
            unchecked.append(
                f"contour {ci} v{vi} ({v['kind']}): neighbours only "
                f"{back:.0f}/{fwd:.0f}px away, below --min-baseline "
                f"{args.min_baseline:.0f}px")
            continue

        fi, k = owner[g]
        got = flats[fi].turn_at(k, back, fwd)
        if got is None:
            continue
        want = float(v["turn_deg"])
        if got < min(want * args.turn_frac, want) and got < args.turn_floor:
            mode = "smoothed spike" if v["kind"] == "spike" else "missing kink"
            failures.append(
                f"{mode}: contour {ci} v{vi} ({v['kind']}) at "
                f"({q[0]:.1f},{q[1]:.1f}) — inventory turns {want:.0f}deg over "
                f"{back:.0f}/{fwd:.0f}px, authored path turns {got:.0f}deg")

    # Phantom notches. Searched wider than --tol: a corner placed a little
    # too far away is one imprecise corner (already reported as a missing
    # node), not additionally an invented one.
    radius = args.tol * 3
    for g, (fi, k) in enumerate(owner):
        if g in matched:
            continue
        got = flats[fi].turn_at(k, args.probe, args.probe)
        if got is None or got < args.phantom:
            continue
        d = np.sqrt(((inv_xy - all_nodes[g]) ** 2).sum(1))
        j = int(np.argmin(d))
        if d[j] <= radius and verts[j][2]["kind"] in STRUCTURAL:
            continue
        failures.append(
            f"phantom notch: authored node ({all_nodes[g][0]:.1f},"
            f"{all_nodes[g][1]:.1f}) turns {got:.0f}deg over "
            f"{args.probe:.0f}px but the inventory has no structural vertex "
            f"within {radius:.0f}px (nearest is {verts[j][2]['kind']} at "
            f"{d[j]:.1f}px)")

    kinds = sorted({v["kind"] for _, _, v in verts if v["kind"] in STRUCTURAL})
    n_struct = sum(1 for _, _, v in verts if v["kind"] in STRUCTURAL)
    if failures:
        print(f"FAIL — {len(failures)} conformance violation(s) across "
              f"{n_struct} structural vertices:")
        for f in failures:
            print("  " + f)
        if unchecked:
            print(f"  ({len(unchecked)} vertex/vertices left unchecked:)")
            for u in unchecked:
                print("    " + u)
        return 1
    if not args.quiet:
        print(f"PASS — {n_struct} structural vertices ({', '.join(kinds)}) all "
              f"present as path nodes with their kinks intact; no phantom "
              f"notches among {len(all_nodes)} authored nodes")
        for u in unchecked:
            print(f"  unchecked: {u}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
