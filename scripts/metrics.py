#!/usr/bin/env python3
"""Generate the isometric contribution calendar and a languages card.

Stdlib only. Uses GraphQL when GITHUB_TOKEN is set, otherwise scrapes the
public contributions page so it still works locally and in Actions without
METRICS_TOKEN.

    python scripts/metrics.py --user Vasy420 --out assets
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

UA = {"User-Agent": "metrics.py"}

# GitHub contribution greens (dark profile)
TOP = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
LEFT = ["#11151a", "#0b3a24", "#005a2b", "#1f8f38", "#2ea043"]
RIGHT = ["#0d1117", "#082c1b", "#004720", "#187a2e", "#238636"]
EMPTY_EDGE = "#21262d"
BG = "#0d1117"
TITLE = "#39d353"
MUTED = "#8b949e"
BORDER = "#30363d"
FONT = "ui-sans-serif,-apple-system,Segoe UI,Helvetica,Arial,sans-serif"

LANG_COLOR = {
    "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "Python": "#3572A5",
    "HTML": "#e34c26", "CSS": "#563d7c", "C++": "#f34b7d", "C": "#555555",
    "Java": "#b07219", "Go": "#00ADD8", "Rust": "#dea584", "Shell": "#89e051",
    "PHP": "#4F5D95", "Ruby": "#701516", "Vue": "#41b883", "SCSS": "#c6538c",
    "Jupyter Notebook": "#DA5B0B", "PowerShell": "#012456",
}


def rest(path: str, token: str | None):
    req = urllib.request.Request("https://api.github.com" + path, headers=dict(UA))
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def graphql(query: str, variables: dict, token: str):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={**UA, "Content-Type": "application/json",
                 "Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


CONTRIB_QUERY = """
query($login:String!){
  user(login:$login){
    contributionsCollection{
      contributionCalendar{
        totalContributions
        weeks{ contributionDays{ date contributionCount } }
      }
    }
  }
}
"""


def fetch_contributions(user: str, token: str | None):
    """Return (total, [(date, count, level), ...]) covering the last ~year."""
    if token:
        try:
            data = graphql(CONTRIB_QUERY, {"login": user}, token)
            cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
            days = []
            for w in cal["weeks"]:
                for d in w["contributionDays"]:
                    c = int(d["contributionCount"])
                    days.append((dt.date.fromisoformat(d["date"]), c, _level(c)))
            return int(cal["totalContributions"]), days
        except (urllib.error.HTTPError, KeyError, TypeError) as e:
            print(f"  graphql unavailable ({e}), falling back to scrape", file=sys.stderr)
    return scrape_contributions(user)


def scrape_contributions(user: str):
    url = f"https://github.com/users/{user}/contributions"
    req = urllib.request.Request(url, headers=dict(UA))
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", "replace")
    days = []
    for m in re.finditer(
        r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*data-level="(\d+)"', html
    ):
        date = dt.date.fromisoformat(m.group(1))
        level = int(m.group(2))
        days.append((date, level, level))  # count unknown; height uses level
    if not days:
        sys.exit(f"could not scrape contributions for {user}")
    days.sort()
    # tooltip counts if present: "12 contributions on January 1, 2026"
    counts = {}
    for m in re.finditer(
        r'(\d+)\s+contributions?\s+on\s+([A-Za-z]+ \d+, \d{4})', html
    ):
        try:
            counts[dt.datetime.strptime(m.group(2), "%B %d, %Y").date()] = int(m.group(1))
        except ValueError:
            pass
    if counts:
        days = [(d, counts.get(d, c), lv) for d, c, lv in days]
        total = sum(counts.values())
    else:
        total = sum(1 for _, c, lv in days if lv > 0)
    return total, days


def _level(count: int) -> int:
    if count <= 0:
        return 0
    if count == 1:
        return 1
    if count <= 3:
        return 2
    if count <= 6:
        return 3
    return 4


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# --------------------------------------------------------------------------- #
# isometric calendar
# --------------------------------------------------------------------------- #

DX, DY = 14, 8
BASE_H = 3
LEVEL_H = [0, 7, 11, 16, 22]


def _cube(cx, cy, h, level):
    """Three faces of an isometric cube. cy is the top of the *base* (no height)."""
    top_y = cy - h
    t, l, r = TOP[level], LEFT[level], RIGHT[level]
    edge = EMPTY_EDGE if level == 0 else "#0d1117"
    top = (
        f"{cx:.1f},{top_y:.1f} {cx + DX:.1f},{top_y + DY:.1f} "
        f"{cx:.1f},{top_y + 2 * DY:.1f} {cx - DX:.1f},{top_y + DY:.1f}"
    )
    left = (
        f"{cx - DX:.1f},{top_y + DY:.1f} {cx:.1f},{top_y + 2 * DY:.1f} "
        f"{cx:.1f},{cy + 2 * DY:.1f} {cx - DX:.1f},{cy + DY:.1f}"
    )
    right = (
        f"{cx + DX:.1f},{top_y + DY:.1f} {cx:.1f},{top_y + 2 * DY:.1f} "
        f"{cx:.1f},{cy + 2 * DY:.1f} {cx + DX:.1f},{cy + DY:.1f}"
    )
    sw = 0.6
    return (
        f'<polygon points="{left}" fill="{l}" stroke="{edge}" stroke-width="{sw}"/>'
        f'<polygon points="{right}" fill="{r}" stroke="{edge}" stroke-width="{sw}"/>'
        f'<polygon points="{top}" fill="{t}" stroke="{edge}" stroke-width="{sw}"/>'
    )


def render_isocalendar(user: str, total: int, days: list, theme="dark") -> str:
    if not days:
        sys.exit("no contribution days")
    days = sorted(days)
    # pad to full weeks starting Sunday
    start = days[0][0]
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)  # Sunday
    end = days[-1][0]
    by = {d: (c, lv) for d, c, lv in days}

    cells = []  # (week, dow, count, level, date)
    d = start
    week = 0
    while d <= end:
        dow = (d.weekday() + 1) % 7  # Sun=0
        c, lv = by.get(d, (0, 0))
        cells.append((week, dow, c, lv, d))
        if dow == 6:
            week += 1
        d += dt.timedelta(days=1)
    nweeks = week if cells and cells[-1][1] == 6 else week + 1

    # origin so the whole grid sits in positive space with a margin
    margin = 28
    title_h = 36
    # bounding box of isometric grid
    def pos(w, dow):
        return (w - dow) * DX, (w + dow) * DY

    xs, ys = [], []
    for w, dow, c, lv, date in cells:
        px, py = pos(w, dow)
        h = BASE_H + LEVEL_H[lv]
        xs += [px - DX, px + DX]
        ys += [py - h, py + 2 * DY]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    W = int(maxx - minx + 2 * margin)
    H = int(maxy - miny + 2 * margin + title_h)
    ox, oy = -minx + margin, -miny + margin + title_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" '
        f'aria-label="{esc(user)} contribution calendar" font-family="{FONT}">',
        f'<rect width="100%" height="100%" rx="10" fill="{BG}" stroke="{BORDER}"/>',
        f'<text x="{margin}" y="24" font-size="15" font-weight="700" fill="{TITLE}">'
        f'{esc(user)} · last 12 months</text>',
        f'<text x="{W - margin}" y="24" font-size="12" text-anchor="end" fill="{MUTED}">'
        f'{total:,} contributions</text>',
        f'<g transform="translate({ox:.1f},{oy:.1f})">',
    ]

    # back to front
    ordered = sorted(cells, key=lambda t: (t[0] + t[1], t[0]))
    for w, dow, c, lv, date in ordered:
        px, py = pos(w, dow)
        h = BASE_H + LEVEL_H[lv]
        parts.append(_cube(px, py, h, lv))

    # month labels along the Sunday row
    last_month = None
    for w, dow, c, lv, date in cells:
        if dow != 0:
            continue
        if date.month == last_month:
            continue
        last_month = date.month
        px, py = pos(w, 0)
        parts.append(
            f'<text x="{px:.1f}" y="{py - 10:.1f}" font-size="10" fill="{MUTED}" '
            f'text-anchor="middle">{date.strftime("%b")}</text>'
        )

    parts.append("</g></svg>")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# languages card
# --------------------------------------------------------------------------- #


def fetch_languages(user: str, token: str | None, limit=8):
    totals: dict[str, int] = {}
    page = 1
    while True:
        batch = rest(
            f"/users/{user}/repos?per_page=100&page={page}&type=owner&sort=pushed",
            token,
        )
        if not batch:
            break
        for repo in batch:
            if repo.get("fork") or repo.get("archived"):
                continue
            try:
                langs = rest(repo["languages_url"].replace("https://api.github.com", ""), token)
            except urllib.error.HTTPError:
                continue
            for name, n in langs.items():
                if name.lower() in {"html", "css", "shell", "makefile", "dockerfile",
                                    "batchfile", "powershell", "procfile"}:
                    continue
                totals[name] = totals.get(name, 0) + n
        if len(batch) < 100:
            break
        page += 1
    top = sorted(totals.items(), key=lambda kv: -kv[1])[:limit]
    return top


def render_languages(user: str, langs: list, theme="dark") -> str:
    W, pad = 420, 18
    row_h = 28
    H = pad + 28 + max(len(langs), 1) * row_h + pad
    total = sum(n for _, n in langs) or 1
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" '
        f'aria-label="{esc(user)} most used languages" font-family="{FONT}">',
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" '
        f'fill="{BG}" stroke="{BORDER}"/>',
        f'<text x="{pad}" y="{pad + 14}" font-size="14" font-weight="700" fill="{TITLE}">'
        f'Most used languages</text>',
    ]
    bar_x = pad + 110
    bar_w = W - pad - bar_x - 54
    y = pad + 40
    for name, n in langs:
        pct = 100 * n / total
        col = LANG_COLOR.get(name, MUTED)
        parts.append(
            f'<text x="{pad}" y="{y}" font-size="12" fill="#c9d1d9">{esc(name)}</text>'
        )
        parts.append(
            f'<rect x="{bar_x}" y="{y - 10}" width="{bar_w}" height="8" rx="4" fill="#21262d"/>'
        )
        parts.append(
            f'<rect x="{bar_x}" y="{y - 10}" width="{bar_w * n / total:.1f}" height="8" '
            f'rx="4" fill="{col}"/>'
        )
        parts.append(
            f'<text x="{W - pad}" y="{y}" font-size="11" text-anchor="end" fill="{MUTED}">'
            f'{pct:.1f}%</text>'
        )
        y += row_h
    parts.append("</svg>")
    return "".join(parts)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--user", required=True)
    p.add_argument("--out", type=Path, default=Path("assets"))
    args = p.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    total, days = fetch_contributions(args.user, token)
    iso = args.out / "metrics.isocalendar.svg"
    iso.write_text(render_isocalendar(args.user, total, days), encoding="utf-8")
    print(f"wrote {iso}  ({total} contributions, {len(days)} days)")

    langs = fetch_languages(args.user, token)
    if langs:
        dest = args.out / "metrics.languages.svg"
        dest.write_text(render_languages(args.user, langs), encoding="utf-8")
        print(f"wrote {dest}  ({len(langs)} languages)")


if __name__ == "__main__":
    main()
