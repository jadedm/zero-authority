#!/usr/bin/env python3
"""Fetch the league and write data.json for the static page.

The page is client-side and cannot call FPL itself: the API sends no
Access-Control-Allow-Origin header, so a browser on any other origin refuses to
read the response. Verified, not assumed. So the fetching happens here, server
side, where CORS does not apply, and the page reads the file this produces.

The league rules are encoded once, in settle(), and the page only renders. That
way the sheet cannot disagree with itself.

Run: python build.py
"""

import json
import sys
import urllib.request
from datetime import datetime, timezone

LEAGUE = 1151779
API = "https://fantasy.premierleague.com/api"
UA = "zero-authority settlement sheet (github.com/jadedm/zero-authority)"

ENTRY_FEE = 1000
LAST_PLACE_PENALTY = 1000
PRIZE_OVERALL = 3000
PRIZE_GW_WINS = 1000


class Incomplete(Exception):
    """Refuse to publish a half-fetched sheet."""


def get(path: str):
    req = urllib.request.Request(f"{API}/{path}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def all_fixtures_played(gw: int) -> bool:
    """A gameweek counts only once every fixture in it has finished.

    Scoring a week that is still running would hand out coffees nobody owes yet,
    and would name a gameweek winner who might not be one by Monday night.
    """
    fx = get(f"fixtures/?event={gw}")
    return bool(fx) and all(f.get("finished_provisional") or f.get("finished") for f in fx)


def gather() -> dict:
    league = get(f"leagues-classic/{LEAGUE}/standings/")
    rows = league["standings"]["results"]
    if not rows:
        raise Incomplete("the league standings came back empty")

    managers = []
    for row in rows:
        h = get(f"entry/{row['entry']}/history/")
        managers.append({
            "team": row["entry_name"],
            "name": row["player_name"],
            "total": row["total"],
            "weeks": {str(g["event"]): g["points"] for g in h["current"]},
        })

    played = sorted({int(g) for m in managers for g in m["weeks"]})
    if not played:
        raise Incomplete("no gameweeks have been played yet")

    settled, live = [], []
    for gw in played:
        (settled if all_fixtures_played(gw) else live).append(gw)

    return {"league": league["league"]["name"], "managers": managers,
            "settled": settled, "live": live}


def settle(d: dict) -> dict:
    """Money and coffees as they stand if the season ended now."""
    ms = sorted(d["managers"], key=lambda m: -m["total"])
    wins = {m["team"]: [] for m in ms}
    for gw in d["settled"]:
        scores = {m["team"]: m["weeks"][str(gw)] for m in ms if str(gw) in m["weeks"]}
        if not scores:
            continue
        best = max(scores.values())
        for team, pts in scores.items():
            if pts == best:
                wins[team].append(gw)          # a drawn week counts for both

    most = max((len(v) for v in wins.values()), default=0)
    leaders = [t for t, v in wins.items() if len(v) == most and most > 0]

    for i, m in enumerate(ms):
        m["pos"] = i + 1
        m["gap"] = ms[0]["total"] - m["total"]
        m["win_gws"] = wins[m["team"]]
        m["wins"] = len(m["win_gws"])
        m["is_last"] = i == len(ms) - 1
        paid = ENTRY_FEE + (LAST_PLACE_PENALTY if m["is_last"] else 0)
        won = PRIZE_OVERALL if i == 0 else 0
        if m["team"] in leaders:
            won += PRIZE_GW_WINS // len(leaders)   # a tie splits it
        m["net"] = won - paid
        m["coffees"] = m["wins"] * (len(ms) - 1) - sum(
            len(v) for t, v in wins.items() if t != m["team"])

    if sum(m["net"] for m in ms) != 0:
        raise Incomplete("the money does not sum to zero; the rules are misapplied")

    return {
        "league": d["league"],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "settled": d["settled"],
        "live": d["live"],
        "rules": {"entry": ENTRY_FEE, "penalty": LAST_PLACE_PENALTY,
                  "overall": PRIZE_OVERALL, "gw_wins": PRIZE_GW_WINS,
                  "pool": ENTRY_FEE * len(ms) + LAST_PLACE_PENALTY},
        "table": ms,
        "win_leaders": leaders,
        "most_wins": most,
    }


def main() -> int:
    try:
        out = settle(gather())
    except Incomplete as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:                    # a partial file is worse than none
        print(f"fetch failed, leaving data.json untouched: {exc}", file=sys.stderr)
        return 1
    with open("data.json", "w") as fh:
        json.dump(out, fh, indent=2, allow_nan=False)
    print(f"wrote data.json: {len(out['table'])} managers, "
          f"gameweeks settled {out['settled']}, in play {out['live'] or 'none'}")
    for m in out["table"]:
        print(f"  {m['pos']}. {m['team']:16} {m['total']:4} "
              f"wins {m['wins']}  net {m['net']:+5}  coffees {m['coffees']:+d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
