# AeroHealth alert integration notes

## Integrated into this backend

- Reused `accounts.UserProfile`; no second alert-profile identity model was added.
- Added alert preferences and consent fields to account profiles, with migration `accounts.0002_alert_preferences`.
- Implemented alert rules, logs, saved locations, alert state, employer organizations, message templates, smoke plume prediction storage and meteorological reading storage in `backend/alerts`.
- Added current AQI priority: fresh station observation within 10 km → fresh satellite/model grid estimate within 25 km → existing Open-Meteo + XGBoost estimate.
- Added forecast priority: fresh stored `weather.AQIForecast` records with uncertainty bounds → existing dashboard daily forecast fallback.
- Added five-language alert copy, persona-derived defaults, user guidance sensitivity, quiet hours, daily cap, cooldown/escalation, all-clear notifications and channel opt-outs.
- Added FCM, Twilio SMS/voice adapters, phone OTP verification and signature-validated Twilio STOP webhook.
- Added user APIs, saved locations, privacy-preserving employer aggregates, Celery task/beat configuration and management commands.
- Added account-page controls for language, sensitivity, alert enablement and explicit consent.

## Migrations to apply

- `accounts.0002_alert_preferences`
- `airquality.0002_ground_and_grid_readings`
- `alerts.0001_initial`

Run `python manage.py migrate` before starting the app.

## Data/provider integration still required

- The uploaded project contained no populated station readings or satellite AQI grid. Import real records using `import_ground_readings` and `import_aqi_grid`; otherwise the current Open-Meteo + XGBoost estimate is used and labelled as a model estimate.
- No smoke plume trajectory dataset/model was present. `SmokeDriftPrediction` and `import_smoke_predictions` accept its output; FIRMS hotspots alone are not treated as smoke-arrival proof.
- No boundary-layer observations were present. `WeatherReading` and `import_weather_readings` accept wind and boundary-layer data; stagnation alerts remain inactive until such rows exist.
- FCM credentials and a browser FCM token-registration flow must be configured to use push. Twilio credentials are required for SMS/voice and OTP.
- Thresholds and multilingual health guidance are informational product defaults and need public-health/native-language review before deployment.

## Verification

Python syntax compilation (`compileall` and AST parsing) passed in the packaging environment. Django runtime tests and migrations could not be executed here because Django and the project's requirements are not installed in this environment. Run `python manage.py test alerts` and the full project test suite after installing `requirements.txt`.
