#!/usr/bin/env python3
"""Render Abel's GitHub contributions as a hotel at night (SVG).

- Fetches the public contributions page (no token needed).
- Draws one window per day: lit windows = days with commits.
- Writes hotel-windows.svg and bumps the ?v= cache-buster in README.md.
"""
import datetime
import os
import re
import urllib.request

USER = "aichrisz"
URL = f"https://github.com/users/{USER}/contributions"
UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "Chrome/120 Safari/537.36"
}

LEVEL_COLORS = {
    0: "#1b2440",  # dark window
    1: "#7d5f31",  # dim
    2: "#c99a3f",  # lit
    3: "#f2c14e",  # bright
    4: "#ffe08a",  # blazing
}

CELL, GAP = 9, 3
STEP = CELL + GAP
LEFT, TOP = 22, 34


def fetch_html():
    req = urllib.request.Request(URL, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def parse_days(html):
    days = {}
    for tag in re.findall(r"<[^>]*data-date=\"\d{4}-\d{2}-\d{2}\"[^>]*>", html):
        d = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', tag)
        lv = re.search(r'data-level="([0-4])"', tag)
        if d and lv:
            days[d.group(1)] = int(lv.group(1))
    if not days:
        raise SystemExit("No contribution days parsed; page format may have changed")
    return days


def parse_total(html):
    m = re.search(r"([\d,]+) contributions in the last year", html)
    return m.group(1) if m else "?"


def build_weeks(days):
    dates = sorted(days)
    first = datetime.date.fromisoformat(dates[0])
    # GitHub weeks start on Sunday
    start = first - datetime.timedelta(days=(first.weekday() + 1) % 7)
    weeks = {}
    for ds in dates:
        d = datetime.date.fromisoformat(ds)
        col = (d - start).days // 7
        row = (d.weekday() + 1) % 7  # Sunday = 0
        weeks.setdefault(col, {})[row] = days[ds]
    ncols = max(weeks) + 1
    return weeks, ncols


def render_svg(weeks, ncols, total):
    w = LEFT * 2 + ncols * STEP - GAP
    h = TOP + 7 * STEP - GAP + 46
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" font-family="monospace">',
        f'<rect x="4" y="22" width="{w - 8}" height="{h - 26}" rx="10" fill="#141b2e"/>',
        # roof sign
        f'<text x="{w / 2}" y="15" text-anchor="middle" font-size="11" '
        f'fill="#f2c14e" letter-spacing="4">★ HOTEL</text>',
    ]
    # windows
    for col in range(ncols):
        for row in range(7):
            level = weeks.get(col, {}).get(row, 0)
            x = LEFT + col * STEP
            y = TOP + row * STEP
            parts.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                f'fill="{LEVEL_COLORS[level]}"/>'
            )
    # caption
    parts.append(
        f'<text x="{w / 2}" y="{h - 8}" text-anchor="middle" font-size="10" '
        f'fill="#8b93a7">{total} contributions in the last year · '
        f'lit windows = days with commits</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def bump_readme_cache():
    today = datetime.date.today().strftime("%Y%m%d")
    with open("README.md", encoding="utf-8") as f:
        text = f.read()
    new_text, n = re.subn(
        r"hotel-windows\.svg\?v=\d{8}", f"hotel-windows.svg?v={today}", text
    )
    if n == 0:
        raise SystemExit("hotel-windows.svg?v= marker not found in README.md")
    if new_text != text:
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(new_text)


def main():
    html = fetch_html()
    days = parse_days(html)
    total = parse_total(html)
    weeks, ncols = build_weeks(days)
    svg = render_svg(weeks, ncols, total)
    with open("hotel-windows.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"rendered {ncols} weeks, {len(days)} days, total {total}")
    bump_readme_cache()


if __name__ == "__main__":
    main()
