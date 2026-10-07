#!/usr/bin/env python3
"""Rotate the authenticated user's GitHub profile status from a pool.

Required env vars:
  STATUS_TOKEN  PAT with the `user` scope.

Optional env vars:
  STATUS_POOL_FILE   Path to a JSON file of [{"emoji": ":x:", "message": "..."}].
                     Defaults to scripts/pool.json next to this file.
  STATUS_EXPIRY_MIN  Minutes until the status auto-clears. Default 65.
  STATUS_BUSY        "true" to mark limited availability. Default false.
"""
from __future__ import annotations

import json
import os
import random
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

GRAPHQL = "https://api.github.com/graphql"
MUTATION = """
mutation($input: ChangeUserStatusInput!) {
  changeUserStatus(input: $input) {
    status { message emoji expiresAt }
  }
}
"""


def load_pool() -> list[tuple[str, str]]:
    path = Path(os.environ.get("STATUS_POOL_FILE") or Path(__file__).with_name("pool.json"))
    data = json.loads(path.read_text())
    pool = [(entry["emoji"], entry["message"]) for entry in data]
    if not pool:
        raise SystemExit(f"pool at {path} is empty")
    return pool


def main() -> int:
    token = os.environ.get("STATUS_TOKEN")
    if not token:
        print("STATUS_TOKEN env var missing", file=sys.stderr)
        return 1

    emoji, message = random.choice(load_pool())
    expiry_min = int(os.environ.get("STATUS_EXPIRY_MIN", "65"))
    busy = os.environ.get("STATUS_BUSY", "").lower() == "true"
    expires = (datetime.now(timezone.utc) + timedelta(minutes=expiry_min)).isoformat()

    payload = json.dumps({
        "query": MUTATION,
        "variables": {
            "input": {
                "emoji": emoji,
                "message": message,
                "expiresAt": expires,
                "limitedAvailability": busy,
            }
        },
    }).encode()

    req = urllib.request.Request(
        GRAPHQL,
        data=payload,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "github-status-rotator",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        return 1

    if body.get("errors"):
        print(json.dumps(body["errors"], indent=2), file=sys.stderr)
        return 1

    result = body["data"]["changeUserStatus"]["status"]
    print(f"set status -> {result['emoji']} {result['message']} (expires {result['expiresAt']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
