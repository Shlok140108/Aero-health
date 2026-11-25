# AeroHealth

Air-quality and temperature prediction for India, served through a Django REST API.

## What it does
- **Temperature forecast** – hybrid approach:
  - within 30 km of one of 10 known cities → that city's **Prophet** model
  - anywhere else in India → national **XGBoost** model (lat, lon, month, day of year)
- **AQI estimation** – XGBoost trained on CPCB station data (pollutants + location + month/weekday)
- **Live weather** – conventional weather page (`/weather/`): current conditions, 24 h strip, 7-day forecast, wind/humidity/UV/pressure/visibility/sun tiles, AQI, °C/°F toggle. Works worldwide (Open-Meteo); CPCB AQI estimate only inside India.
- **Live location tracker** – browser GPS (`watchPosition`) with a map, accuracy ring, trail and speed/heading; weather + place name refresh automatically after you move ~500 m. City search in the top bar. The dashboard and prediction pages follow your location too.
- **Data pipeline** – ingestion scripts for CPCB air quality, Open-Meteo weather and NASA FIRMS fire data

## Results (honest summary)
| Task | Result | Note |
|---|---|---|
| AQI from pollutants | R² 0.93, MAE ≈ 20.8 | This is *estimation*: AQI is computed from PM2.5/PM10, so a high score is expected |
| Next-day AQI (215 stations) | MAE ≈ 15.6 vs 16.1 for the "tomorrow = today" baseline | Time-based split; only a small gain over the baseline |

## Run it
```bash
pip install -r requirements.txt
python manage.py runserver
./demo.sh            # in a second terminal
python manage.py test          # 28 tests, upstream APIs are mocked
```

## API
`POST /api/weather/predict-temperature/`
```json
{"lat": 18.52, "lon": 73.85, "date": "2026-11-15"}
```
```json
{"predicted_temperature": 24.9, "model_used": "prophet", "matched_city": "Pune"}
```

`GET /api/live/?lat=&lon=` · `GET /api/geocode/?q=` · `GET /api/reverse/?lat=&lon=` · `GET /api/overview/` · `GET /api/prediction/`

> Browsers only share GPS on `https://` or `http://localhost`. Open the app at `http://localhost:8000` (not a LAN IP) for live tracking.
> Needs internet access to `api.open-meteo.com`, `air-quality-api.open-meteo.com`, `geocoding-api.open-meteo.com` and `nominatim.openstreetmap.org` (map tiles: `tile.openstreetmap.org`).

## Project layout
```
backend/         Django apps (weather, airquality, alerts)
datascience/     ingestion scripts and notebooks
models/          trained model files
aerohealth/      Django project settings
```

## Status / roadmap
- [x] Temperature prediction API with tests
- [x] AQI model and next-day forecasting experiments
- [ ] AQI prediction endpoint
- [x] Alert app integrated with account profiles: AQI/forecast rules, consent, history, saved locations, SMS/voice verification, FCM/Twilio adapters (dry-run by default)
- [ ] Live smoke-plume and stagnation ingestion (schemas/import commands are provided; real plume/meteorological feeds still need to be connected)
- [x] Frontend dashboard, live weather page, live location tracker
- [ ] Docker deployment

> Models are loaded with `pickle`; only load model files you trust.

## Personalized alerts

The `backend/alerts` app is integrated with `accounts.UserProfile` (there is no duplicate alert-profile table and no GeoDjango requirement). It supports persona-derived AQI thresholds, guidance sensitivity, five message languages, explicit consent, quiet hours, cooldowns, daily caps, alert history, saved locations and privacy-preserving employer aggregates.

Current AQI and forecast alerts use the existing Open-Meteo + XGBoost dashboard services, and are labelled as model estimates. If persisted `weather.AQIForecast` rows exist, their uncertainty bounds are included. FCM and Twilio are optional and live delivery is disabled by default.

```bash
python manage.py migrate
python manage.py test alerts
python manage.py evaluate_alerts             # safe dry-run
python manage.py evaluate_alerts --send      # live delivery after provider configuration
```

See [`backend/alerts/README.md`](backend/alerts/README.md) for endpoints, provider setup, scheduler instructions and current data limitations.
