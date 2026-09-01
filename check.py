#!/usr/bin/env python3
"""Assert data.json is a sheet worth publishing.

build.py refuses to write a bad file, but a file that is merely stale or subtly
wrong would still publish. These are the properties a reader would be misled by
if they were false.
"""
import json
import sys

FAIL = []


def check(cond, msg):
    if not cond:
        FAIL.append(msg)


d = json.load(open("data.json"))
t = d["table"]

check(len(t) >= 2, "fewer than two managers")
check(sum(m["net"] for m in t) == 0, "the money does not sum to zero")
check(sum(m["coffees"] for m in t) == 0, "the coffee ledger does not sum to zero")
check([m["pos"] for m in t] == list(range(1, len(t) + 1)), "positions are not 1..n")
check(all(t[i]["total"] >= t[i + 1]["total"] for i in range(len(t) - 1)),
      "the table is not sorted by total")
check(t[0]["gap"] == 0, "the leader has a non-zero gap")
check(d["settled"], "no settled gameweeks")
check(not set(d["settled"]) & set(d["live"]), "a gameweek is both settled and live")
# every settled gameweek must have exactly one recorded winner set
for gw in d["settled"]:
    winners = [m for m in t if gw in m["win_gws"]]
    check(winners, f"gameweek {gw} has no winner")
    best = max(m["weeks"][str(gw)] for m in t if str(gw) in m["weeks"])
    check(all(m["weeks"][str(gw)] == best for m in winners),
          f"gameweek {gw} names a winner who did not top it")

if FAIL:
    for f in FAIL:
        print(f"check failed: {f}", file=sys.stderr)
    sys.exit(1)
print(f"ok: {len(t)} managers, gameweeks {d['settled']} settled, money and coffees balance")
