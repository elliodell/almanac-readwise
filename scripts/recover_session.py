#!/usr/bin/env python3
"""Inspect a single uncertain session; releasing a retry requires explicit confirmation."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import urllib.parse
from setup_readwise import Readwise, account_root, load


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--card", type=Path, required=True)
    p.add_argument("--session", required=True, help="64-character filename from the private queue")
    p.add_argument("--retry-confirmed-absent", action="store_true")
    args = p.parse_args()
    if not re.fullmatch("[0-9a-f]{64}", args.session):
        p.error("Invalid session filename")
    card = args.card.resolve()
    cfg = load(card / ".crosspoint/readwise-books/config.json")
    root = account_root(card, cfg["token"])
    base = root / "history" / args.session
    request_path = Path(str(base) + ".request")
    attempt = Path(str(base) + ".attempt")
    receipt = Path(str(base) + ".receipt.json")
    if receipt.exists():
        p.error("A receipt exists; this session must not be retried")
    raw = request_path.read_bytes()
    if attempt.read_text() != hashlib.sha256(raw).hexdigest():
        p.error("The attempt marker is damaged or the request changed; preserve these files for investigation")
    item = json.loads(raw)["items"][0]
    query = urllib.parse.urlencode({"book_ids": item["book_id"], "started_after": item["started_at"],
                                   "started_before": item["ended_at"], "include_deleted": "true", "limit": 1000})
    response = Readwise(cfg["token"]).request("sessions?" + query)
    # Conservative: ANY session in the window prevents a manual reset. The
    # reader can reconcile an exact match on its next Wi-Fi connection.
    if response.get("next") or not isinstance(response.get("results"), list) or response["results"]:
        print("Readwise has sessions in this time window, or results are incomplete. No retry released.")
        print("Reconnect the reader to Wi-Fi for automatic reconciliation.")
        return
    print("Readwise currently reports no sessions for this book in the attempted time window.")
    if not args.retry_confirmed_absent:
        print("No files changed. If you independently confirm the session is absent, rerun with --retry-confirmed-absent.")
        return
    print("A delayed server result could still appear. Only retry after checking the Books app.")
    if input("Type RETRY to allow one new attempt: ") != "RETRY":
        return
    # Keep the marker for an audit trail; never change the frozen request.
    archived = Path(str(base) + ".attempt.before-manual-retry")
    if archived.exists():
        p.error("This session was already manually retried; preserve it for investigation")
    attempt.rename(archived)
    print("One retry released. Safely eject and reconnect the reader to Wi-Fi.")


if __name__ == "__main__":
    main()
