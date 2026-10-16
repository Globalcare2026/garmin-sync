# Garmin Sync

Automatischer täglicher Export von Garmin Connect Daten nach OneDrive via GitHub Actions.

## Was wird gezogen

- **Daily**: RHR, Schritte, Kalorien, Intensity Minutes, Stress, Body Battery, SpO2
- **Sleep**: Gesamt, Tief, Light, REM, Awake, Scores, Respiration
- **HRV**: Last Night Avg, Baseline, Status
- **Training Readiness**: Score, Sleep Factor, Recovery Time, Acute Load
- **Activities**: alle Aktivitäten mit HR, TE, Distanz, Load
- **VO2max**: Running & Cycling aktuell + Fitness Age
- **Race Predictions**: 5K, 10K, HM, Marathon

Alles landet als CSV im Repo unter `data/latest/`, mit täglichem Snapshot unter `data/archive/YYYY-MM-DD/`.

## Setup (einmalig, geht auch am Handy)

### 1. Zwei GitHub Secrets setzen

Repo -> Settings -> Secrets and variables -> Actions -> New repository secret:

| Secret | Wert |
|---|---|
| `GARMIN_EMAIL` | spitzle79@gmail.com |
| `GARMIN_PASSWORD` | dein Garmin-Passwort |

### 2. Erster Testlauf

Actions -> "Daily Garmin Sync" -> Run workflow

Bei aktiver Garmin-2FA bricht der erste Login ab: 2FA kurz deaktivieren, einmal laufen lassen, wieder aktivieren. Der Login-Token wird danach gecacht.

### 3. Fertig

Läuft täglich um 08:15 (Amsterdam). Die Daten liegen im Repo unter `data/latest/` plus täglichem Snapshot unter `data/archive/YYYY-MM-DD/`.

## Lokal testen

```bash
pip install -r requirements.txt
export GARMIN_EMAIL=spitzle79@gmail.com
export GARMIN_PASSWORD=dein-passwort
python sync.py
ls out/
```

## Dashboard

Claude liest die CSVs direkt aus diesem Repo und frischt das Dashboard auf Zuruf oder nach Zeitplan.

## Troubleshooting

- **Token expired**: GitHub Actions Cache löschen (Settings -> Caches), neuer Run holt frische Tokens
- **MFA Fehler**: siehe Option A/B oben
