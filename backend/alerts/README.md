# AeroHealth alerts app

This app is integrated with the existing `accounts.UserProfile`; it does **not** create a second user/profile system and does not require GeoDjango/PostGIS.

## What is connected now

- Current AQI checks first use fresh `airquality.GroundReading` rows from a CPCB station within 10 km, then fresh `airquality.AQIGridPoint` rows (satellite/model grid) within 25 km, then the existing Open-Meteo pollutant + XGBoost estimator. Each source is logged distinctly.
- Forecast alerts first use existing `weather.AQIForecast` rows (including `confidence_lower` / `confidence_upper`). If there are no nearby stored rows, they use the existing `dashboard.api.build_prediction()` daily AQI estimates for the next 72 hours.
- Persona is derived from the existing account profile fields (`conditions`, age, occupation and outdoor hours). The alerts app does not store diagnoses separately.
- User language (English, Hindi, Marathi, Tamil, Bengali), guidance sensitivity, explicit consent, channels, quiet hours and daily limits live on `accounts.UserProfile`.
- Saved locations, alert rules, alert logs, organization membership and alert state are stored in this app.
- FCM push and Twilio SMS/voice are optional provider integrations. No provider sends until the operator disables dry-run and configures credentials. SMS/voice also require verified phone ownership. The browser still needs to register an FCM device token through the settings API before push can be delivered.
- Twilio inbound STOP webhook disables SMS and voice for the matching phone number after signature validation.

## API (requires a signed-in user unless noted)

- `GET/PATCH /api/alerts/settings/` — alert consent, language, sensitivity, channels and quiet hours.
- `GET /api/alerts/rules/`, `PATCH /api/alerts/rules/<id>/` — persona defaults and user overrides.
- `GET /api/alerts/logs/` — current user's notification history.
- `GET/POST /api/alerts/locations/`, `DELETE /api/alerts/locations/<id>/` — saved places (maximum 20).
- `POST /api/alerts/preview/` — preview messages; never sends.
- `POST /api/alerts/phone/request-otp/`, `POST /api/alerts/phone/confirm-otp/` — verify SMS/voice destination.
- `POST /api/alerts/organizations/`, `POST /api/alerts/organizations/<id>/join/`, `GET /api/alerts/organizations/<id>/dashboard/` — employer workspace. Aggregate breakdown is withheld below three members.
- `POST /api/alerts/evaluate/` and `GET /api/alerts/stats/` — admin only.
- `POST /api/alerts/webhooks/twilio-sms/` — Twilio STOP webhook.

Settings PATCH example (consent is explicit):

```json
{
  "consent": true,
  "alerts_enabled": true,
  "alert_language": "en",
  "guidance_sensitivity": "sensitive",
  "push_enabled": false,
  "notify_sms": true,
  "voice_enabled": false,
  "quiet_start": "22:00:00",
  "quiet_end": "07:00:00",
  "alert_timezone": "Asia/Kolkata"
}
```

## Run locally

```bash
python manage.py migrate
python manage.py test alerts
python manage.py evaluate_alerts             # dry-run, safe default
python manage.py evaluate_alerts --send      # live delivery; only after provider setup
```

For scheduled evaluation, configure Redis and run:

```bash
celery -A aerohealth worker --loglevel=info
celery -A aerohealth beat --loglevel=info
```

## Provider environment variables

```env
ALERTS_DRY_RUN=True
REDIS_URL=redis://localhost:6379/0
FIREBASE_SERVICE_ACCOUNT_FILE=/absolute/path/to/firebase-service-account.json
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
ALERTS_TWILIO_WEBHOOK_URL=https://your-domain.example/api/alerts/webhooks/twilio-sms/
```

## Important data limitations

- The supplied project archive does not include populated CPCB station readings or satellite grid estimates. Until those are imported, current AQI alerts fall back to the Open-Meteo + XGBoost estimate. The app labels the source and does not present the fallback as a live sensor reading. TROPOMI itself is not fetched by this alert app; the calibrated grid CSV must come from your satellite/data pipeline.
- Import station and grid data with `python manage.py import_ground_readings path.csv` and `python manage.py import_aqi_grid path.csv`. CSV headers are documented in each command help.
- Smoke alerts are activated only after a plume-drift pipeline imports real predicted plume coordinates using `python manage.py import_smoke_predictions path.csv`. FIRMS hotspot data alone is not proof that smoke will reach a user.
- Stagnation alerts are activated only after valid wind-speed and boundary-layer-height readings are imported using `python manage.py import_weather_readings path.csv`. The ventilation-index cutoff is a configurable screening heuristic, not a validated dispersion model.
- Stored AQI forecast uncertainty is shown only when the forecast row contains calibrated lower/upper bounds. The fallback forecast does not invent confidence percentages.
- Persona thresholds and advice are product defaults, not clinically validated medical guidance. Native-language and public-health review is required before public deployment.
- The employer endpoint exposes aggregate counts only, and withholds the breakdown until at least three members have joined. It does not expose personal health details.
