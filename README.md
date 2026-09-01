# zero authority

Settlement sheet for a three-manager Fantasy Premier League side bet.

**https://jadedm.github.io/zero-authority/**

The FPL site shows the league table. It does not show the thing that actually matters between
three people who have money on it: who is currently paying whom, and why.

## Rules

1,000 rupees entry each, plus 1,000 from whoever finishes last, making a 4,000 pool.

- 3,000 to the overall winner
- 1,000 to whoever wins the most gameweeks
- a coffee to each gameweek's winner, from the other two

A gameweek counts only once every fixture in it has been played, so a week in progress never
awards a win or a coffee.

## How it works

The page is static and reads `data.json`. It does not call the FPL API, because that API sends no
`Access-Control-Allow-Origin` header, so a browser on any other origin refuses to read the
response. The fetching happens in `build.py`, run by a scheduled GitHub Action where CORS does not
apply.

`build.py` writes nothing if the fetch is incomplete, so a bad run leaves the last good sheet
published rather than replacing it with a partial one. `check.py` then asserts the sheet is
coherent before it goes out: the money must sum to zero, the coffee ledger must sum to zero, the
table must be sorted, and every gameweek named as won must actually have been topped by the
manager credited with it.

```
python build.py && python check.py && open index.html
```

## What is public here

The three managers' names, team names and gameweek scores. All of it is already visible to anyone
with the league code on FPL's own site.
