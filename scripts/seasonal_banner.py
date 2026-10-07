#!/usr/bin/env python3
"""Swap lobby-banner.gif for the seasonal variant based on today's date.

Seasons:
  halloween: Oct 15 - Nov 2
  christmas: Dec 1 - Jan 6
  default:   otherwise

Copies assets/banner-<season>.gif over lobby-banner.gif when different.
Env TODAY (YYYY-MM-DD) overrides the date, for testing.
"""
import datetime
import hashlib
import os
import shutil
import sys

ASSETS = {
    "default": "assets/banner-default.gif",
    "halloween": "assets/banner-halloween.gif",
    "christmas": "assets/banner-christmas.gif",
}
TARGET = "lobby-banner.gif"


def season_for(date):
    m, d = date.month, date.day
    if (m == 10 and d >= 15) or (m == 11 and d <= 2):
        return "halloween"
    if m == 12 or (m == 1 and d <= 6):
        return "christmas"
    return "default"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    today = os.environ.get("TODAY") or datetime.date.today().isoformat()
    date = datetime.date.fromisoformat(today)
    season = season_for(date)
    src = ASSETS[season]
    if not os.path.exists(src):
        print(f"asset missing: {src}", file=sys.stderr)
        sys.exit(1)
    if os.path.exists(TARGET) and sha(src) == sha(TARGET):
        print(f"already showing {season}, nothing to do")
        return
    shutil.copyfile(src, TARGET)
    print(f"switched lobby banner to {season}")


if __name__ == "__main__":
    main()
