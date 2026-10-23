#!/usr/bin/env python3
"""
Garmin Connect -> CSV sync for David Haussmann.
Pulls last N days of health & performance metrics from Garmin Connect
and writes them as CSVs into ./out/ for upload to OneDrive by the workflow.
"""

import os
import sys
import json
import csv
import pathlib
from datetime import date, timedelta, datetime

try:
    from garminconnect import (
        Garmin,
        GarminConnectAuthenticationError,
        GarminConnectConnectionError,
        GarminConnectTooManyRequestsError,
    )
except ImportError:
    print("ERROR: pip install garminconnect", file=sys.stderr)
    sys.exit(1)


OUT = pathlib.Path("out")
OUT.mkdir(exist_ok=True)

EMAIL = os.environ.get("GARMIN_EMAIL")
PASSWORD = os.environ.get("GARMIN_PASSWORD")
MFA_TOKEN = os.environ.get("GARMIN_MFA")  # optional
DAYS_BACK = int(os.environ.get("DAYS_BACK", "14"))
TOKENSTORE = os.environ.get("GARMIN_TOKENSTORE", ".garmin_tokens")


def login():
    """Log in to Garmin, caching tokens to avoid MFA on every run."""
    if not EMAIL or not PASSWORD:
        print("ERROR: GARMIN_EMAIL and GARMIN_PASSWORD env vars required", file=sys.stderr)
        sys.exit(1)

    api = Garmin(EMAIL, PASSWORD, is_cn=False)
    try:
        api.login(TOKENSTORE)
        print(f"Logged in using cached tokens at {TOKENSTORE}")
    except (FileNotFoundError, GarminConnectAuthenticationError):
        print("No valid tokens, logging in fresh...")
        if MFA_TOKEN:
            api.login(prompt_mfa=lambda: MFA_TOKEN)
        else:
            api.login()
        api.garth.dump(TOKENSTORE)
        print(f"Fresh login OK, tokens saved to {TOKENSTORE}")
    return api


def write_csv(name, rows, headers):
    if not rows:
        print(f"  SKIP {name}: no rows")
        return
    path = OUT / f"{name}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"  OK   {name}: {len(rows)} rows -> {path}")


def pull_daily(api, days):
    """Pull daily summaries, sleep, HRV, stress, Body Battery, Training Readiness."""
    today = date.today()
    daily, sleep, hrv_rows, readiness_rows, stress_rows = [], [], [], [], []

    for i in range(days):
        d = today - timedelta(days=i)
        ds = d.isoformat()

        # Daily summary (RHR, steps, calories, intensity)
        try:
            s = api.get_user_summary(ds) or {}
            daily.append({
                "date": ds,
                "restingHR": s.get("restingHeartRate"),
                "steps": s.get("totalSteps") or s.get("wellnessTotalSteps"),
                "calories": s.get("totalKilocalories"),
                "activeCalories": s.get("activeKilocalories"),
                "intensityMinutes": (s.get("moderateIntensityMinutes") or 0) + 2 * (s.get("vigorousIntensityMinutes") or 0),
                "floorsClimbed": s.get("floorsAscended"),
                "stressAvg": s.get("averageStressLevel"),
                "bodyBatteryHighest": s.get("bodyBatteryHighestValue"),
                "bodyBatteryLowest": s.get("bodyBatteryLowestValue"),
                "spo2Avg": s.get("averageSpo2"),
            })
        except Exception as e:
            print(f"  WARN daily {ds}: {e}", file=sys.stderr)

        # Sleep
        try:
            sl = api.get_sleep_data(ds) or {}
            dto = sl.get("dailySleepDTO", {}) or {}
            scores = dto.get("sleepScores", {}) or {}
            deep = dto.get("deepSleepSeconds") or 0
            light = dto.get("lightSleepSeconds") or 0
            rem = dto.get("remSleepSeconds") or 0
            awake = dto.get("awakeSleepSeconds") or 0
            total_h = (deep + light + rem) / 3600 if (deep + light + rem) else None
            overall = scores.get("overall", {})
            sleep.append({
                "date": ds,
                "totalHours": round(total_h, 2) if total_h else None,
                "deepHours": round(deep / 3600, 2),
                "lightHours": round(light / 3600, 2),
                "remHours": round(rem / 3600, 2),
                "awakeHours": round(awake / 3600, 2),
                "overallScore": overall.get("value") if isinstance(overall, dict) else None,
                "qualityScore": (scores.get("quality", {}) or {}).get("value"),
                "durationScore": (scores.get("duration", {}) or {}).get("value"),
                "avgSleepStress": dto.get("avgSleepStress"),
                "averageRespiration": dto.get("averageRespirationValue"),
            })
        except Exception as e:
            print(f"  WARN sleep {ds}: {e}", file=sys.stderr)

        # HRV
        try:
            h = api.get_hrv_data(ds) or {}
            summary = h.get("hrvSummary", {}) or {}
            hrv_rows.append({
                "date": ds,
                "lastNightAvg": summary.get("lastNightAvg"),
                "lastNight5MinHigh": summary.get("lastNight5MinHigh"),
                "weeklyAvg": summary.get("weeklyAvg"),
                "baselineLow": (summary.get("baseline") or {}).get("lowUpper"),
                "baselineBalanced": (summary.get("baseline") or {}).get("balancedLow"),
                "status": summary.get("status"),
            })
        except Exception as e:
            print(f"  WARN hrv {ds}: {e}", file=sys.stderr)

        # Training Readiness
        try:
            tr = api.get_training_readiness(ds) or []
            if tr and isinstance(tr, list):
                r0 = tr[0]
                readiness_rows.append({
                    "date": ds,
                    "score": r0.get("score"),
                    "level": r0.get("level"),
                    "sleepScore": r0.get("sleepScore"),
                    "sleepHistoryFactor": r0.get("sleepHistoryFactorFeedback"),
                    "recoveryTime": r0.get("recoveryTime"),
                    "acuteLoad": r0.get("acuteLoad"),
                    "hrvWeeklyAverage": r0.get("hrvWeeklyAverage"),
                    "stressHistoryFactor": r0.get("stressHistoryFactorFeedback"),
                })
        except Exception as e:
            print(f"  WARN readiness {ds}: {e}", file=sys.stderr)

    write_csv("daily", daily, list(daily[0].keys()) if daily else [])
    write_csv("sleep", sleep, list(sleep[0].keys()) if sleep else [])
    write_csv("hrv", hrv_rows, list(hrv_rows[0].keys()) if hrv_rows else [])
    write_csv("training_readiness", readiness_rows, list(readiness_rows[0].keys()) if readiness_rows else [])


def pull_activities(api, days, start=None, name="activities"):
    """Pull activities from the last N days (or from a fixed start date)."""
    today = date.today()
    start = start or (today - timedelta(days=days))
    try:
        acts = api.get_activities_by_date(start.isoformat(), today.isoformat()) or []
    except Exception as e:
        print(f"  WARN activities: {e}", file=sys.stderr)
        return
    rows = []
    for a in acts:
        rows.append({
            "activityId": a.get("activityId"),
            "startTime": a.get("startTimeLocal"),
            "name": a.get("activityName"),
            "type": (a.get("activityType") or {}).get("typeKey") if isinstance(a.get("activityType"), dict) else a.get("activityType"),
            "durationSec": a.get("duration"),
            "distanceM": a.get("distance"),
            "avgHR": a.get("averageHR"),
            "maxHR": a.get("maxHR"),
            "calories": a.get("calories"),
            "aerobicTE": a.get("aerobicTrainingEffect"),
            "anaerobicTE": a.get("anaerobicTrainingEffect"),
            "activityTrainingLoad": a.get("activityTrainingLoad"),
            "vo2Max": a.get("vO2MaxValue"),
        })
    rows.sort(key=lambda r: r["startTime"] or "")
    write_csv(name, rows, list(rows[0].keys()) if rows else [])


def _vo2_from(obj):
    """Extract (running, cycling, fitnessAge) from a Garmin metrics payload of unknown shape."""
    if isinstance(obj, list):
        for item in obj:
            r = _vo2_from(item)
            if r[0] or r[1]:
                return r
        return (None, None, None)
    if not isinstance(obj, dict):
        return (None, None, None)
    if "mostRecentVO2Max" in obj:
        obj = obj.get("mostRecentVO2Max") or {}
    gen = obj.get("generic") or {}
    cyc = obj.get("cycling") or {}
    run = gen.get("vo2MaxPreciseValue") or gen.get("vo2MaxValue")
    bike = cyc.get("vo2MaxPreciseValue") or cyc.get("vo2MaxValue")
    return (run, bike, gen.get("fitnessAge"))


def pull_vo2(api):
    """VO2max: tries max metrics, then training status, then latest run activity."""
    today = date.today().isoformat()
    run = bike = fitness_age = None
    source = None
    for name, call in (
        ("max_metrics", lambda: api.get_max_metrics(today)),
        ("training_status", lambda: api.get_training_status(today)),
    ):
        try:
            payload = call()
        except Exception as e:
            print(f"  WARN vo2 {name}: {e}", file=sys.stderr)
            continue
        r, b, fa = _vo2_from(payload)
        if r or b:
            run, bike, fitness_age, source = r, b, fa, name
            break
    if not (run or bike):
        try:
            acts = api.get_activities(0, 20) or []
            for a in acts:
                if a.get("vO2MaxValue"):
                    run, source = a.get("vO2MaxValue"), "latest_activity"
                    break
        except Exception as e:
            print(f"  WARN vo2 activities: {e}", file=sys.stderr)
    if not (run or bike):
        print("  SKIP vo2max: no value found")
        return
    rows = [{
        "date": today,
        "vo2MaxRunning": run,
        "vo2MaxCycling": bike,
        "fitnessAge": fitness_age,
        "source": source,
    }]
    write_csv("vo2max", rows, list(rows[0].keys()))


def pull_race_predictions(api):
    try:
        rp = api.get_race_predictions() or {}
    except Exception as e:
        print(f"  WARN race_predictions: {e}", file=sys.stderr)
        return
    if not rp:
        return
    rows = [{
        "date": rp.get("calendarDate") or date.today().isoformat(),
        "time5K": rp.get("time5K"),
        "time10K": rp.get("time10K"),
        "timeHalfMarathon": rp.get("timeHalfMarathon"),
        "timeMarathon": rp.get("timeMarathon"),
    }]
    write_csv("race_predictions", rows, list(rows[0].keys()))


def main():
    history_from = os.environ.get("HISTORY_FROM")
    if history_from:
        print(f"=== Garmin history: activities since {history_from} ===")
        api = login()
        pull_activities(api, 0, start=date.fromisoformat(history_from), name="activities_history")
        return
    print(f"=== Garmin sync: {date.today()}, {DAYS_BACK} days back ===")
    api = login()
    print("\n-- Daily summaries, sleep, HRV, readiness --")
    pull_daily(api, DAYS_BACK)
    print("\n-- Activities --")
    pull_activities(api, DAYS_BACK)
    print("\n-- VO2max --")
    pull_vo2(api)
    print("\n-- Race predictions --")
    pull_race_predictions(api)

    # Write metadata
    with (OUT / "_meta.json").open("w") as f:
        json.dump({
            "lastSync": datetime.utcnow().isoformat() + "Z",
            "daysBack": DAYS_BACK,
            "user": EMAIL,
        }, f, indent=2)
    print(f"\n=== Done. Files in {OUT.resolve()} ===")


if __name__ == "__main__":
    main()
