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

Alles landet als CSV in `OneDrive/Gesundheit/Garmin/`, mit täglichem Snapshot unter `/archive/YYYY-MM-DD/`.

## Setup (einmalig)

### 1. GitHub Secrets setzen

Repo -> Settings -> Secrets and variables -> Actions -> New repository secret:

| Secret | Wert |
|---|---|
| `GARMIN_EMAIL` | spitzle79@gmail.com |
| `GARMIN_PASSWORD` | dein Garmin-Passwort |
| `RCLONE_CONFIG` | Inhalt deiner rclone.conf (siehe Schritt 2) |

### 2. rclone OneDrive-Setup

Auf deinem Laptop einmal ausführen:

```bash
# Windows (PowerShell): winget install Rclone.Rclone
# Mac/Linux: brew install rclone  oder  curl https://rclone.org/install.sh | sudo bash

rclone config
# n (new remote)
# name: onedrive
# storage: 32  (Microsoft OneDrive)
# client_id/secret: leer lassen (Enter, Enter)
# region: 1 (Global)
# edit advanced config: n
# use auto config: y  -> Browser-OAuth öffnet
# type: 1 (OneDrive Personal) oder 2 (Business, je nach Account)
# wähle das richtige Drive aus
# Yes -> OK -> q
```

Dann den Inhalt der `rclone.conf` holen:

```bash
# Windows: notepad %APPDATA%\rclone\rclone.conf
# Mac/Linux: cat ~/.config/rclone/rclone.conf
```

Den **kompletten Inhalt** (Zeilen `[onedrive]` bis Ende) als Wert des Secret `RCLONE_CONFIG` einfügen.

### 3. Erster manueller Test

GitHub -> Actions -> "Daily Garmin Sync" -> Run workflow

Falls Garmin 2FA aktiviert hat: beim ersten Login wird's abbrechen. Fix:

**Option A: 2FA bei Garmin kurz deaktivieren** für den initialen Token-Fetch, danach wieder einschalten (Token bleibt gültig).

**Option B: Lokal einmal einloggen** und den `.garmin_tokens`-Ordner als Base64-Secret hinterlegen. Details auf Nachfrage.

### 4. Fertig

Script läuft dann täglich automatisch um 08:15 Amsterdam. CSVs liegen in `OneDrive/Gesundheit/Garmin/`.

## Lokal testen

```bash
pip install -r requirements.txt
export GARMIN_EMAIL=spitzle79@gmail.com
export GARMIN_PASSWORD=dein-passwort
python sync.py
ls out/
```

## Dashboard

Claude liest die CSVs aus OneDrive via Microsoft 365 Connector und frischt das Dashboard auf Zuruf oder nach Zeitplan.

## Troubleshooting

- **Token expired**: GitHub Actions Cache löschen (Settings -> Caches), neuer Run holt frische Tokens
- **MFA Fehler**: siehe Option A/B oben
- **rclone upload fehlt**: Token kann ablaufen, dann einmal lokal `rclone config reconnect onedrive:` und neuen `rclone.conf`-Inhalt ins Secret kopieren
