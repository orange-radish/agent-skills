#!/usr/bin/env python3
"""vd-to-svg.py — render stand-in for Android VectorDrawable XML.

Converts a VectorDrawable to an equivalent SVG so it can be rendered with
rsvg-convert during the iterate loop. It is a STAND-IN: SVG renderers and
Android's renderer disagree on some inputs (see "Android renderer pitfalls"
in `outputs/android-vectordrawable.md`), so a matching stand-in render does
not prove the drawable is right. The final check is a capture with Android's
own renderer (`procedures/render-compare-iterate.md`, "Android
VectorDrawable").

Handled:
  <vector>     viewport -> viewBox; android:alpha -> group opacity
  <group>      translateX/Y, scaleX/Y, rotation, pivotX/Y, composed the way
               Android composes them:
                 translate(tx+px, ty+py) rotate(r) scale(sx, sy) translate(-px, -py)
  <clip-path>  clips every LATER sibling in its group (and their children),
               as on Android; several clip-paths in one group intersect
  <path>       pathData, fillColor, fillAlpha, fillType, strokeColor,
               strokeAlpha, strokeWidth, strokeLineCap, strokeLineJoin,
               strokeMiterLimit; linear and radial <gradient> fills/strokes
               given as <aapt:attr>

Not handled (reported on stderr):
  trimPathStart/End/Offset, sweep gradients, colour resources that were not
  supplied with --color (@color/x, ?attr/x render as #000000)

The arc check: any arc segment spanning 180 deg or more is reported, because
the SVG render will look right even where Android's does not.

Usage:
  python3 vd-to-svg.py IN.xml OUT.svg [--color @color/brand=#FF6A00 ...]

Then:
  rsvg-convert -w 512 -h 512 OUT.svg -o stand-in.png

Requires: Python >= 3.10, standard library only.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
import xml.etree.ElementTree as ET

A = "{http://schemas.android.com/apk/res/android}"
AAPT = "{http://schemas.android.com/aapt}"
SVG = "http://www.w3.org/2000/svg"

LINECAP = {"butt": "butt", "round": "round", "square": "square"}
LINEJOIN = {"miter": "miter", "round": "round", "bevel": "bevel"}


def warn(msg: str) -> None:
    print(f"warning: {msg}", file=sys.stderr)


def num(s: str | None, default: float) -> float:
    if s is None:
        return default
    return float(s.removesuffix("dp").removesuffix("px"))


def fmt(v: float) -> str:
    return f"{v:.6g}"


# ---------------------------------------------------------------- arc check

_TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_ARITY = {"m": 2, "l": 2, "h": 1, "v": 1, "c": 6, "s": 4, "q": 4, "t": 2, "a": 7, "z": 0}


def _segments(d: str):
    """Yield (command, args) with arc flags parsed as single characters."""
    pos, cmd = 0, None
    while pos < len(d):
        while pos < len(d) and d[pos] in " \t\r\n,":
            pos += 1
        if pos >= len(d):
            return
        if d[pos].isalpha():
            cmd = d[pos]
            pos += 1
            if cmd in "Zz":
                yield cmd, []
                continue
        if cmd is None:
            raise ValueError(f"path data must start with a command: {d[:20]!r}")
        args = []
        for i in range(_ARITY[cmd.lower()]):
            while pos < len(d) and d[pos] in " \t\r\n,":
                pos += 1
            if cmd in "Aa" and i in (3, 4):
                args.append(float(d[pos]))
                pos += 1
                continue
            m = _TOKEN.match(d, pos)
            if not m or m.group().isalpha():
                raise ValueError(f"bad path data near {d[pos:pos + 20]!r}")
            args.append(float(m.group()))
            pos = m.end()
        yield cmd, args
        if cmd == "M":
            cmd = "L"
        elif cmd == "m":
            cmd = "l"


def wide_arcs(d: str) -> list[float]:
    """Sweep in degrees of every arc segment spanning >= 180 deg."""
    out = []
    x = y = sx = sy = 0.0
    for cmd, a in _segments(d):
        rel = cmd.islower()
        c = cmd.upper()
        if c == "Z":
            x, y = sx, sy
            continue
        if c == "H":
            x = a[0] + (x if rel else 0)
            continue
        if c == "V":
            y = a[0] + (y if rel else 0)
            continue
        nx, ny = a[-2] + (x if rel else 0), a[-1] + (y if rel else 0)
        if c == "A":
            rx, ry, phi, large = abs(a[0]), abs(a[1]), math.radians(a[2]), a[3]
            if rx and ry:
                dx, dy = (x - nx) / 2, (y - ny) / 2
                ux = (math.cos(phi) * dx + math.sin(phi) * dy) / rx
                uy = (-math.sin(phi) * dx + math.cos(phi) * dy) / ry
                half = min(1.0, math.hypot(ux, uy))
                sweep = math.degrees(2 * math.asin(half))
                if large:
                    sweep = 360 - sweep
                if sweep >= 179.9:
                    out.append(sweep)
        x, y = nx, ny
        if c == "M":
            sx, sy = x, y
    return out


# ------------------------------------------------------------------ colours

def parse_color(value: str, colors: dict[str, str]) -> tuple[str, float]:
    """Return (#rrggbb, alpha) for an Android colour literal or resource."""
    if value in colors:
        value = colors[value]
    if not value.startswith("#"):
        warn(f"unresolved colour {value!r} rendered as #000000; pass --color {value}=#RRGGBB")
        return "#000000", 1.0
    h = value[1:]
    if len(h) in (3, 4):
        h = "".join(ch * 2 for ch in h)
    if len(h) == 6:
        return "#" + h.lower(), 1.0
    if len(h) == 8:
        return "#" + h[2:].lower(), int(h[:2], 16) / 255
    raise ValueError(f"bad colour {value!r}")


class Converter:
    def __init__(self, colors: dict[str, str]):
        self.colors = colors
        self.defs: ET.Element | None = None
        self.ids = 0

    def new_id(self, prefix: str) -> str:
        self.ids += 1
        return f"{prefix}{self.ids}"

    def gradient(self, el: ET.Element) -> str:
        kind = el.get(A + "type", "linear")
        if kind == "sweep":
            warn("sweep gradient not supported; rendered as its start colour")
            return parse_color(el.get(A + "startColor", "#000"), self.colors)[0]
        gid = self.new_id("g")
        if kind == "linear":
            g = ET.SubElement(self.defs, "linearGradient", id=gid,
                              x1=el.get(A + "startX", "0"), y1=el.get(A + "startY", "0"),
                              x2=el.get(A + "endX", "0"), y2=el.get(A + "endY", "0"))
        else:
            g = ET.SubElement(self.defs, "radialGradient", id=gid,
                              cx=el.get(A + "centerX", "0"), cy=el.get(A + "centerY", "0"),
                              r=el.get(A + "gradientRadius", "0"))
        g.set("gradientUnits", "userSpaceOnUse")
        tile = el.get(A + "tileMode", "clamp")
        if tile != "clamp":
            g.set("spreadMethod", {"repeat": "repeat", "mirror": "reflect"}.get(tile, "pad"))
        items = el.findall("item")
        if items:
            stops = [(item.get(A + "offset", "0"), item.get(A + "color")) for item in items]
        else:
            stops = [("0", el.get(A + "startColor"))]
            if el.get(A + "centerColor"):
                stops.append(("0.5", el.get(A + "centerColor")))
            stops.append(("1", el.get(A + "endColor")))
        for offset, color in stops:
            rgb, alpha = parse_color(color or "#000", self.colors)
            stop = ET.SubElement(g, "stop", offset=offset)
            stop.set("stop-color", rgb)
            if alpha < 1:
                stop.set("stop-opacity", fmt(alpha))
        return f"url(#{gid})"

    def paint(self, el: ET.Element, attr: str) -> tuple[str, float] | None:
        for child in el.findall(AAPT + "attr"):
            if child.get("name") == "android:" + attr:
                grad = child.find("gradient")
                if grad is not None:
                    return self.gradient(grad), 1.0
        value = el.get(A + attr)
        if value is None:
            return None
        return parse_color(value, self.colors)

    def path(self, el: ET.Element, parent: ET.Element, label: str) -> None:
        d = el.get(A + "pathData", "")
        for sweep in wide_arcs(d):
            warn(f"{label}: arc spanning {sweep:.0f} deg; split it into arcs of 90 deg or less "
                 "(see outputs/android-vectordrawable.md, renderer pitfalls)")
        for attr in ("trimPathStart", "trimPathEnd", "trimPathOffset"):
            if el.get(A + attr) is not None:
                warn(f"{label}: {attr} not supported; rendered untrimmed")
        p = ET.SubElement(parent, "path", d=d)
        fill = self.paint(el, "fillColor")
        if fill is None:
            p.set("fill", "none")
        else:
            p.set("fill", fill[0])
            alpha = fill[1] * num(el.get(A + "fillAlpha"), 1)
            if alpha < 1:
                p.set("fill-opacity", fmt(alpha))
            if el.get(A + "fillType") == "evenOdd":
                p.set("fill-rule", "evenodd")
        stroke = self.paint(el, "strokeColor")
        width = num(el.get(A + "strokeWidth"), 0)
        if stroke is not None and width > 0:
            p.set("stroke", stroke[0])
            p.set("stroke-width", fmt(width))
            alpha = stroke[1] * num(el.get(A + "strokeAlpha"), 1)
            if alpha < 1:
                p.set("stroke-opacity", fmt(alpha))
            p.set("stroke-linecap", LINECAP[el.get(A + "strokeLineCap", "butt")])
            p.set("stroke-linejoin", LINEJOIN[el.get(A + "strokeLineJoin", "miter")])
            # Android's default miter limit is 4, which is also SVG's.
            p.set("stroke-miterlimit", fmt(num(el.get(A + "strokeMiterLimit"), 4)))

    def children(self, src: ET.Element, out: ET.Element, label: str) -> None:
        target = out
        for i, child in enumerate(src):
            name = child.get(A + "name") or f"{child.tag}[{i}]"
            if child.tag == "group":
                self.group(child, target, f"{label}/{name}")
            elif child.tag == "path":
                self.path(child, target, f"{label}/{name}")
            elif child.tag == "clip-path":
                d = child.get(A + "pathData", "")
                for sweep in wide_arcs(d):
                    warn(f"{label}/{name}: clip arc spanning {sweep:.0f} deg; split it")
                cid = self.new_id("c")
                clip = ET.SubElement(self.defs, "clipPath", id=cid)
                ET.SubElement(clip, "path", d=d)
                target = ET.SubElement(target, "g", {"clip-path": f"url(#{cid})"})

    def group(self, src: ET.Element, parent: ET.Element, label: str) -> None:
        tx, ty = num(src.get(A + "translateX"), 0), num(src.get(A + "translateY"), 0)
        px, py = num(src.get(A + "pivotX"), 0), num(src.get(A + "pivotY"), 0)
        sx, sy = num(src.get(A + "scaleX"), 1), num(src.get(A + "scaleY"), 1)
        r = num(src.get(A + "rotation"), 0)
        g = ET.SubElement(parent, "g")
        ops = []
        if tx + px or ty + py:
            ops.append(f"translate({fmt(tx + px)} {fmt(ty + py)})")
        if r:
            ops.append(f"rotate({fmt(r)})")
        if sx != 1 or sy != 1:
            ops.append(f"scale({fmt(sx)} {fmt(sy)})")
        if px or py:
            ops.append(f"translate({fmt(-px)} {fmt(-py)})")
        if ops:
            g.set("transform", " ".join(ops))
        self.children(src, g, label)

    def convert(self, root: ET.Element) -> ET.Element:
        if root.tag != "vector":
            raise ValueError(f"root element is <{root.tag}>, expected <vector>")
        vw = num(root.get(A + "viewportWidth"), 0)
        vh = num(root.get(A + "viewportHeight"), 0)
        svg = ET.Element("svg", xmlns=SVG, viewBox=f"0 0 {fmt(vw)} {fmt(vh)}",
                         width=fmt(vw), height=fmt(vh))
        self.defs = ET.SubElement(svg, "defs")
        top = ET.SubElement(svg, "g")
        alpha = num(root.get(A + "alpha"), 1)
        if alpha < 1:
            top.set("opacity", fmt(alpha))
        if root.get(A + "tint"):
            warn(f"android:tint={root.get(A + 'tint')} ignored; the stand-in shows untinted fills")
        self.children(root, top, "vector")
        if not len(self.defs):
            svg.remove(self.defs)
        return svg


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--color", action="append", default=[], metavar="REF=#HEX",
                    help="resolve a colour resource, e.g. @color/brand=#FF6A00")
    args = ap.parse_args()
    colors = dict(item.split("=", 1) for item in args.color)
    svg = Converter(colors).convert(ET.parse(args.input).getroot())
    ET.indent(svg)
    ET.ElementTree(svg).write(args.output, encoding="unicode", xml_declaration=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
