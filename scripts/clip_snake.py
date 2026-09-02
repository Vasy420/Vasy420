#!/usr/bin/env python3
"""Pad and clip Platane/snk SVGs so the snake stays inside the frame."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def clip(svg: str, pad: float = 12) -> str:
    m = re.search(r'viewBox="([^"]+)"', svg)
    if not m:
        return svg
    x, y, w, h = (float(v) for v in m.group(1).split())
    x -= pad
    y -= pad
    w += 2 * pad
    h += 2 * pad
    vb = f'viewBox="{x:.0f} {y:.0f} {w:.0f} {h:.0f}"'
    svg = svg.replace(m.group(0), vb, 1)
    svg = re.sub(r'\bwidth="[^"]+"', f'width="{w:.0f}"', svg, count=1)
    svg = re.sub(r'\bheight="[^"]+"', f'height="{h:.0f}"', svg, count=1)
    svg = re.sub(r"\soverflow=\"[^\"]*\"", "", svg, count=1)
    svg = svg.replace("<svg", '<svg overflow="hidden"', 1)
    clip_id = "snakeBox"
    defs = (
        f'<defs><clipPath id="{clip_id}">'
        f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}"/>'
        f"</clipPath></defs>"
        f'<g clip-path="url(#{clip_id})">'
    )
    # Insert after the opening <svg ...> tag.
    svg = re.sub(r"(<svg\b[^>]*>)", r"\1" + defs, svg, count=1)
    svg = svg.replace("</svg>", "</g></svg>", 1)
    return svg


def main():
    p = argparse.ArgumentParser()
    p.add_argument("paths", nargs="+", type=Path)
    p.add_argument("--pad", type=float, default=12)
    args = p.parse_args()
    for path in args.paths:
        if not path.exists():
            print(f"skip {path}")
            continue
        path.write_text(clip(path.read_text(encoding="utf-8"), args.pad), encoding="utf-8")
        print(f"clipped {path}")


if __name__ == "__main__":
    main()
