#!/usr/bin/env python3
"""Merge data/latest/activities.csv into data/history/activities_history.csv (keyed by activityId)."""
import csv, pathlib
latest = pathlib.Path("data/latest/activities.csv")
hist = pathlib.Path("data/history/activities_history.csv")
if not latest.exists():
    print("no latest activities, nothing to merge"); raise SystemExit
rows = {}
if hist.exists():
    for r in csv.DictReader(hist.open(encoding="utf-8")):
        rows[r["activityId"]] = r
headers = None
new = 0
for r in csv.DictReader(latest.open(encoding="utf-8")):
    headers = headers or list(r.keys())
    if r["activityId"] not in rows:
        new += 1
    rows[r["activityId"]] = r
if headers is None:
    print("latest empty"); raise SystemExit
hist.parent.mkdir(parents=True, exist_ok=True)
with hist.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
    w.writeheader()
    for r in sorted(rows.values(), key=lambda x: x.get("startTime") or ""):
        w.writerow(r)
print(f"history: {len(rows)} activities, {new} new")
