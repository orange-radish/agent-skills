#!/usr/bin/env python3
"""inspect-outline.py — feature-inventory JSON for image-to-vector skill.

Single source of truth for vertex/segment thresholds (no other skill file
restates these numbers — by design):

  vertex turn-angle:
    <10°       drop (not a real corner)
    10°-30°    smooth (curve continues through)
    30°-80°    corner (kink — two distinct segments)
    80°-150°   sharp_corner
    >150°      spike (V-tip / path-direction reversal)

  segment classification between consecutive non-smooth vertices:
    mean|κ|<0.002 px⁻¹ AND max|κ|<0.01 px⁻¹       → line
    sign(κ) constant AND stdev|κ|/mean|κ|<0.3     → arc
    length < 5 px after RDP                       → line
    terminates at a spike vertex                  → spike_reversal
    otherwise                                     → curve_freeform

Usage:
  python3 inspect-outline.py INPUT [--out OUT.json] [--render-overlay OVL.png]
                              [--strip-effects auto|none] [--rdp-epsilon 1.0]

Requires: Pillow + NumPy (see tools/requirements.txt). Python ≥ 3.10.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


# ---------------------------------------------------------------------------
# Binarization + effect detection
# ---------------------------------------------------------------------------

def _border_mode_color(rgb: np.ndarray, band: int = 4) -> np.ndarray:
    h, w, _ = rgb.shape
    border = np.concatenate([
        rgb[:band].reshape(-1, 3),
        rgb[-band:].reshape(-1, 3),
        rgb[:, :band].reshape(-1, 3),
        rgb[:, -band:].reshape(-1, 3),
    ])
    # mode via quantized histogram
    q = (border // 8).astype(np.int32)
    keys = q[:, 0] * (32 * 32) + q[:, 1] * 32 + q[:, 2]
    vals, counts = np.unique(keys, return_counts=True)
    k = int(vals[int(np.argmax(counts))])
    return np.array([(k // 1024) * 8, ((k // 32) % 32) * 8, (k % 32) * 8], dtype=np.float32)


def binarize(im: Image.Image, strip_effects: str) -> tuple[np.ndarray, str, list[str]]:
    """Return (core_mask float in [0,1], outline_source description, effects_detected)."""
    effects: list[str] = []
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        rgba = np.asarray(im.convert("RGBA"), dtype=np.float32)
        alpha = rgba[..., 3]
        core = (alpha >= 250).astype(np.float32)
        envelope = (alpha >= 30).astype(np.float32)
        core_area = float(core.sum())
        env_area = float(envelope.sum())
        ratio = env_area / max(core_area, 1.0)
        if ratio > 1.3 and core_area > 0:
            # estimate glow radius from area difference (annulus thickness)
            r_core = math.sqrt(core_area / math.pi)
            r_env = math.sqrt(env_area / math.pi)
            glow_r = max(1.0, r_env - r_core)
            effects.append(f"glow:alpha:radius~{glow_r:.0f}px")
        outline_source = f"alpha>=250 (env/core={ratio:.2f})"
        # if user asked --strip-effects none, fall back to envelope mask
        if strip_effects == "none":
            return (alpha / 255.0), f"alpha>=30 (effects retained)", effects
        # use soft alpha so marching squares places contour at subpixel
        # boundary of the core; clip below 250 to 0 so anti-alias outside core is excluded
        field = np.where(alpha >= 250, 1.0, 0.0)
        # add subpixel feathering: blend a half-step between 245-255
        soft = np.clip((alpha - 245.0) / 10.0, 0.0, 1.0)
        field = soft
        return field, outline_source, effects

    # No alpha: detect background color, compute color distance, threshold.
    rgb = np.asarray(im.convert("RGB"), dtype=np.float32)
    bg = _border_mode_color(rgb)
    dist = np.linalg.norm(rgb - bg, axis=2)
    dmax = float(np.percentile(dist, 99.0))
    if dmax < 1e-6:
        return np.zeros(dist.shape, dtype=np.float32), "luminance/otsu (empty)", effects
    core_thresh = 0.5 * dmax
    env_thresh = 0.15 * dmax
    core_mask = (dist > core_thresh).astype(np.float32)
    env_mask = (dist > env_thresh).astype(np.float32)
    core_area = float(core_mask.sum())
    env_area = float(env_mask.sum())
    ratio = env_area / max(core_area, 1.0)
    if ratio > 1.5 and core_area > 0:
        # check that envelope minus core has a distinct dominant color (halo)
        diff = (env_mask - core_mask) > 0
        if diff.sum() > core_area * 0.1:
            mean_diff_color = rgb[diff].mean(axis=0)
            label = _color_label(mean_diff_color, bg)
            r_core = math.sqrt(core_area / math.pi)
            r_env = math.sqrt(env_area / math.pi)
            effects.append(f"halo:{label}:radius~{max(1.0, r_env-r_core):.0f}px")
    if strip_effects == "none":
        return env_mask, f"color-distance > {env_thresh:.0f} (effects retained, bg=#{int(bg[0]):02x}{int(bg[1]):02x}{int(bg[2]):02x})", effects
    # subpixel field: smooth ramp around core_thresh
    field = np.clip((dist - (core_thresh - 4.0)) / 8.0, 0.0, 1.0)
    outline_source = f"color-distance > {core_thresh:.0f} (bg=#{int(bg[0]):02x}{int(bg[1]):02x}{int(bg[2]):02x})"
    return field, outline_source, effects


def _color_label(c: np.ndarray, bg: np.ndarray) -> str:
    r, g, b = c.tolist()
    if b > r + 20 and b > g + 10:
        return "blue"
    if r > g + 20 and r > b + 10:
        return "red"
    if g > r + 10 and g > b + 10:
        return "green"
    if r > 200 and g > 150 and b < 100:
        return "orange"
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


# ---------------------------------------------------------------------------
# Marching squares (inlined; ~50 LOC)
# ---------------------------------------------------------------------------

# Case table keyed by (TL<<3)|(TR<<2)|(BR<<1)|BL, value = list of edge pairs.
_CASES = {
    1:  [('L', 'B')], 2:  [('B', 'R')], 3:  [('L', 'R')],
    4:  [('T', 'R')], 5:  [('T', 'L'), ('B', 'R')],
    6:  [('T', 'B')], 7:  [('T', 'L')],
    8:  [('T', 'L')], 9:  [('T', 'B')],
    10: [('T', 'R'), ('L', 'B')], 11: [('T', 'R')],
    12: [('L', 'R')], 13: [('B', 'R')], 14: [('L', 'B')],
}


def gaussian_blur(arr: np.ndarray, sigma: float = 1.0, ks: int = 5) -> np.ndarray:
    x = np.arange(ks) - ks // 2
    g = np.exp(-(x ** 2) / (2 * sigma ** 2))
    g = g / g.sum()
    out = np.apply_along_axis(lambda v: np.convolve(v, g, mode='same'), 0, arr)
    out = np.apply_along_axis(lambda v: np.convolve(v, g, mode='same'), 1, out)
    return out


def marching_squares(field: np.ndarray, level: float = 0.5) -> list[list[tuple[float, float]]]:
    h, w = field.shape
    bn = (field >= level).astype(np.uint8)
    idx = (bn[:-1, :-1].astype(np.int8) << 3) | (bn[:-1, 1:].astype(np.int8) << 2) \
        | (bn[1:, 1:].astype(np.int8) << 1) | bn[1:, :-1].astype(np.int8)
    mask = (idx != 0) & (idx != 15)
    ys, xs = np.where(mask)
    segs: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for i, j in zip(ys.tolist(), xs.tolist()):
        ci = int(idx[i, j])
        tl = float(field[i, j]); tr = float(field[i, j+1])
        br = float(field[i+1, j+1]); bl = float(field[i+1, j])
        def lerp(a: float, b: float) -> float:
            if a == b:
                return 0.5
            t = (level - a) / (b - a)
            return min(1.0, max(0.0, t))
        T = (j + lerp(tl, tr), float(i))
        R = (float(j + 1), i + lerp(tr, br))
        B = (j + lerp(bl, br), float(i + 1))
        L = (float(j), i + lerp(tl, bl))
        pts = {'T': T, 'R': R, 'B': B, 'L': L}
        for a, b in _CASES[ci]:
            segs.append((pts[a], pts[b]))
    return _chain_segments(segs)


def _chain_segments(segs):
    Q = 1000  # quantize endpoints to 1/1000 px to merge identical points
    def k(p):
        return (int(round(p[0] * Q)), int(round(p[1] * Q)))
    pt_of: dict = {}
    adj: dict = {}
    for eid, (p, q) in enumerate(segs):
        kp, kq = k(p), k(q)
        pt_of.setdefault(kp, p); pt_of.setdefault(kq, q)
        adj.setdefault(kp, []).append((kq, eid))
        adj.setdefault(kq, []).append((kp, eid))
    used: set[int] = set()
    contours: list[list[tuple[float, float]]] = []
    for start in list(pt_of.keys()):
        while True:
            nxt = next(((nk, eid) for (nk, eid) in adj[start] if eid not in used), None)
            if nxt is None:
                break
            loop = [pt_of[start]]
            cur = start
            nk, eid = nxt
            used.add(eid)
            while nk != start:
                loop.append(pt_of[nk])
                step = next(((kk, ee) for (kk, ee) in adj[nk] if ee not in used), None)
                if step is None:
                    break  # open path (touches image edge)
                used.add(step[1])
                cur, nk = nk, step[0]
            if len(loop) >= 4:
                contours.append(loop)
    return contours


# ---------------------------------------------------------------------------
# RDP for closed contours
# ---------------------------------------------------------------------------

def rdp_indices(pts: list[tuple[float, float]], eps: float) -> list[int]:
    n = len(pts)
    if n < 3:
        return list(range(n))
    arr = np.asarray(pts, dtype=np.float64)
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        p1, p2 = arr[a], arr[b]
        seg = p2 - p1
        L = math.hypot(seg[0], seg[1]) + 1e-12
        rel = arr[a + 1:b] - p1
        d = np.abs(rel[:, 0] * seg[1] - rel[:, 1] * seg[0]) / L
        if d.size == 0:
            continue
        k = int(np.argmax(d))
        if float(d[k]) > eps:
            keep[a + 1 + k] = True
            stack.append((a, a + 1 + k))
            stack.append((a + 1 + k, b))
    return [i for i, v in enumerate(keep) if v]


def rdp_closed(pts: list[tuple[float, float]], eps: float) -> list[int]:
    """RDP on a closed contour; returns indices into pts (in order) that survive."""
    n = len(pts)
    if n < 4:
        return list(range(n))
    xs = [p[0] for p in pts]
    a = int(np.argmax(xs))
    b = int(np.argmin(xs))
    if a == b:
        return list(range(n))
    if a < b:
        h1_idx = list(range(a, b + 1))
        h2_idx = list(range(b, n)) + list(range(0, a + 1))
    else:
        h1_idx = list(range(a, n)) + list(range(0, b + 1))
        h2_idx = list(range(b, a + 1))
    h1_pts = [pts[i] for i in h1_idx]
    h2_pts = [pts[i] for i in h2_idx]
    k1 = rdp_indices(h1_pts, eps)
    k2 = rdp_indices(h2_pts, eps)
    kept = [h1_idx[i] for i in k1[:-1]] + [h2_idx[i] for i in k2[:-1]]
    # dedupe while preserving order, then sort by original index
    seen = set(); out = []
    for i in kept:
        if i not in seen:
            seen.add(i); out.append(i)
    out.sort()
    return out


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def signed_area(pts: list[tuple[float, float]]) -> float:
    n = len(pts); s = 0.0
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        s += (x2 - x1) * (y2 + y1)
    return s / 2.0


def turn_angle_deg(p_prev, p, p_next) -> float:
    v1x, v1y = p[0] - p_prev[0], p[1] - p_prev[1]
    v2x, v2y = p_next[0] - p[0], p_next[1] - p[1]
    cross = v1x * v2y - v1y * v2x
    dot = v1x * v2x + v1y * v2y
    return math.degrees(abs(math.atan2(cross, dot)))


def curvature(p_prev, p, p_next) -> float:
    ax, ay = p_prev; bx, by = p; cx, cy = p_next
    ab = math.hypot(bx - ax, by - ay)
    bc = math.hypot(cx - bx, cy - by)
    ac = math.hypot(cx - ax, cy - ay)
    denom = ab * bc * ac
    if denom < 1e-9:
        return 0.0
    cross = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    return 2.0 * cross / denom


def classify_vertex(turn_deg: float) -> str | None:
    if turn_deg < 10.0:    return None
    if turn_deg < 30.0:    return "smooth"
    if turn_deg < 80.0:    return "corner"
    if turn_deg < 150.0:   return "sharp_corner"
    return "spike"


def classify_segment(raw_pts, lo, hi, kind_to_v, length_px) -> tuple[str, dict]:
    """lo, hi are raw-contour indices (lo < hi, segment is raw_pts[lo..hi]).
    kind_to_v: kind of the vertex at raw index hi (the to-vertex)."""
    n = len(raw_pts)
    # Build list of curvatures along the inner samples (excluding endpoints)
    if hi - lo < 2:
        if kind_to_v == "spike":
            return "spike_reversal", {"curvature_mean": 0.0}
        return "line", {"curvature_mean": 0.0}
    ks: list[float] = []
    for m in range(lo + 1, hi):
        ks.append(curvature(raw_pts[m - 1], raw_pts[m], raw_pts[m + 1]))
    arr = np.asarray(ks)
    abs_arr = np.abs(arr)
    mean_abs = float(abs_arr.mean()) if arr.size else 0.0
    max_abs = float(abs_arr.max()) if arr.size else 0.0
    meta = {"curvature_mean": mean_abs, "curvature_max": max_abs}
    if kind_to_v == "spike":
        return "spike_reversal", meta
    if length_px < 5.0:
        return "line", meta
    if mean_abs < 0.002 and max_abs < 0.01:
        return "line", meta
    # arc test: constant sign and low relative stdev
    if arr.size >= 3:
        signs = np.sign(arr)
        if (signs >= 0).all() or (signs <= 0).all():
            std = float(abs_arr.std())
            if mean_abs > 1e-6 and std / mean_abs < 0.3:
                return "arc", meta
    return "curve_freeform", meta


# ---------------------------------------------------------------------------
# Symmetry
# ---------------------------------------------------------------------------

def symmetry_vertical(pts: list[tuple[float, float]]) -> dict | None:
    if len(pts) < 8 or len(pts) > 600:
        return None
    arr = np.asarray(pts, dtype=np.float64)
    cx = float(arr[:, 0].mean())
    refl = arr.copy()
    refl[:, 0] = 2 * cx - refl[:, 0]
    d = np.linalg.norm(arr[:, None, :] - refl[None, :, :], axis=2)
    hd = max(float(d.min(axis=1).max()), float(d.min(axis=0).max()))
    bbox_diag = math.hypot(float(arr[:, 0].ptp()), float(arr[:, 1].ptp())) + 1e-9
    conf = max(0.0, 1.0 - (hd / bbox_diag) * 5.0)
    return {"axis": "vertical", "x": cx, "confidence": round(conf, 3)}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

_BREAK_KINDS = {"corner", "sharp_corner", "spike"}


def _classify_segment_window(seg_pts: list[tuple[float, float]], to_kind: str) -> tuple[str, dict, float]:
    """seg_pts: ordered raw points from segment start to end (inclusive on both ends)."""
    length_px = sum(math.hypot(seg_pts[i+1][0]-seg_pts[i][0], seg_pts[i+1][1]-seg_pts[i][1])
                    for i in range(len(seg_pts) - 1))
    ks: list[float] = []
    for mi in range(1, len(seg_pts) - 1):
        ks.append(curvature(seg_pts[mi - 1], seg_pts[mi], seg_pts[mi + 1]))
    arr = np.asarray(ks); abs_arr = np.abs(arr) if ks else np.zeros(0)
    mean_abs = float(abs_arr.mean()) if abs_arr.size else 0.0
    max_abs = float(abs_arr.max()) if abs_arr.size else 0.0
    meta = {"curvature_mean": round(mean_abs, 5), "curvature_max": round(max_abs, 5)}
    if to_kind == "spike":
        return "spike_reversal", meta, length_px
    if length_px < 5.0:
        return "line", meta, length_px
    if mean_abs < 0.002 and max_abs < 0.01:
        return "line", meta, length_px
    if arr.size >= 3:
        signs = np.sign(arr)
        if ((signs >= 0).all() or (signs <= 0).all()) and mean_abs > 1e-6 and float(abs_arr.std()) / mean_abs < 0.3:
            return "arc", meta, length_px
    return "curve_freeform", meta, length_px


def analyze_contour(raw_pts: list[tuple[float, float]], rdp_eps: float) -> dict:
    n = len(raw_pts)
    kept = rdp_closed(raw_pts, rdp_eps)
    # 1. classify every kept vertex
    m = len(kept)
    if m == 0:
        return {"vertices": [], "segments": [], "symmetry": None}
    vs: list[dict] = []
    for vi in range(m):
        raw_i = kept[vi]
        p_prev = raw_pts[kept[(vi - 1) % m]]
        p_cur = raw_pts[raw_i]
        p_next = raw_pts[kept[(vi + 1) % m]]
        turn = turn_angle_deg(p_prev, p_cur, p_next)
        kind = classify_vertex(turn)
        vs.append({"raw_i": raw_i, "xy": p_cur, "turn_deg": round(turn, 1), "kind": kind})
    # 2. drop sub-10° vertices iteratively
    changed = True
    while changed:
        changed = False
        for vi in range(len(vs)):
            if vs[vi]["kind"] is None:
                del vs[vi]; changed = True
                for vj in range(len(vs)):
                    p_prev = vs[(vj - 1) % len(vs)]["xy"]
                    p_cur = vs[vj]["xy"]
                    p_next = vs[(vj + 1) % len(vs)]["xy"]
                    t = turn_angle_deg(p_prev, p_cur, p_next)
                    vs[vj]["turn_deg"] = round(t, 1)
                    vs[vj]["kind"] = classify_vertex(t)
                break
    if not vs:
        return {"vertices": [], "segments": [], "symmetry": None}
    # 3. break points are corner / sharp_corner / spike vertices; segments span
    #    between consecutive break points (smooth vertices are interior samples)
    break_indices = [i for i, v in enumerate(vs) if v["kind"] in _BREAK_KINDS]
    if not break_indices:
        # entire contour is one closed smooth segment — anchor at vs[0]
        break_indices = [0]
    M = len(vs)

    def _samples_between(a_vi: int, b_vi: int) -> list[tuple[float, float]]:
        a_raw = vs[a_vi]["raw_i"]; b_raw = vs[b_vi]["raw_i"]
        if a_vi == b_vi:
            return raw_pts[a_raw:] + raw_pts[:a_raw + 1]
        if a_raw < b_raw:
            return raw_pts[a_raw:b_raw + 1]
        return raw_pts[a_raw:] + raw_pts[:b_raw + 1]

    segments: list[dict] = []
    B = len(break_indices)
    for bi in range(B):
        a_vi = break_indices[bi]
        b_vi = break_indices[(bi + 1) % B] if B > 1 else a_vi
        seg_pts = _samples_between(a_vi, b_vi if B > 1 else a_vi)
        to_kind = vs[b_vi]["kind"] if B > 1 else "corner"
        kind, meta, length_px = _classify_segment_window(seg_pts, to_kind)
        entry = {"from": a_vi, "to": b_vi, "kind": kind,
                 "length_px": round(length_px, 1), **meta}
        if kind == "spike_reversal":
            entry["tip_index"] = b_vi
        segments.append(entry)
    out_vertices = [{"index": i, "xy": [round(v["xy"][0], 2), round(v["xy"][1], 2)],
                     "kind": v["kind"], "turn_deg": v["turn_deg"]} for i, v in enumerate(vs)]
    return {"vertices": out_vertices, "segments": segments,
            "symmetry": symmetry_vertical([v["xy"] for v in vs])}


def render_overlay(im: Image.Image, contours_data: list[dict], path: Path) -> None:
    overlay = im.convert("RGBA").copy()
    draw = ImageDraw.Draw(overlay)
    KIND_COLOR = {
        "smooth": (255, 255, 0, 255),
        "corner": (255, 128, 0, 255),
        "sharp_corner": (255, 0, 0, 255),
        "spike": (255, 0, 255, 255),
    }
    SEG_COLOR = {
        "line": (0, 255, 0, 200),
        "arc": (0, 200, 255, 200),
        "curve_freeform": (0, 128, 255, 200),
        "spike_reversal": (255, 0, 255, 220),
    }
    for c in contours_data:
        verts = c["vertices"]
        if not verts:
            continue
        for seg in c["segments"]:
            p1 = verts[seg["from"]]["xy"]; p2 = verts[seg["to"]]["xy"]
            draw.line([tuple(p1), tuple(p2)], fill=SEG_COLOR.get(seg["kind"], (255, 255, 255, 200)), width=2)
        for v in verts:
            x, y = v["xy"]; r = 6
            draw.ellipse([(x - r, y - r), (x + r, y + r)], outline=KIND_COLOR.get(v["kind"], (255, 255, 255, 255)), width=2)
    overlay.save(path)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Produce a feature-inventory JSON for a raster.")
    ap.add_argument("input", type=Path)
    ap.add_argument("--out", type=Path, default=None, help="Output JSON path; defaults to stdout.")
    ap.add_argument("--render-overlay", type=Path, default=None)
    ap.add_argument("--strip-effects", choices=("auto", "none"), default="auto")
    ap.add_argument("--rdp-epsilon", type=float, default=1.0)
    args = ap.parse_args(argv)

    im = Image.open(args.input)
    field, outline_source, effects = binarize(im, args.strip_effects)
    # Light Gaussian smoothing reduces sub-pixel jitter (and false corners) from
    # anti-aliased or noisy edges before the contour is extracted.
    field = gaussian_blur(field, sigma=1.0, ks=5)
    raw_contours = marching_squares(field, level=0.5)
    raw_contours.sort(key=lambda c: abs(signed_area(c)), reverse=True)
    contours_out: list[dict] = []
    for ci, raw in enumerate(raw_contours):
        if len(raw) < 8:
            continue
        role = "outer" if ci == 0 else "hole"
        analysis = analyze_contour(raw, args.rdp_epsilon)
        contours_out.append({
            "role": role,
            "signed_area": round(signed_area(raw), 1),
            "raw_vertex_count": len(raw),
            **analysis,
        })

    result = {
        "image": {
            "path": str(args.input),
            "width": im.width,
            "height": im.height,
            "mode": im.mode,
            "outline_source": outline_source,
        },
        "effects_detected": effects,
        "rdp_epsilon": args.rdp_epsilon,
        "contours": contours_out,
    }

    text = json.dumps(result, indent=2)
    if args.out:
        args.out.write_text(text)
    else:
        print(text)
    if args.render_overlay:
        render_overlay(im, contours_out, args.render_overlay)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
