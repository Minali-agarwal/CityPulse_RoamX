# CityPulse — Live Civic Health Dashboard

CityPulse is an intelligent civic telemetry platform that monitors urban vitals across **Weather**, **Traffic**, and **Civic Incidents**, normalizing disparate sensor streams into a unified data schema for real-time situational awareness and civic health scoring.

## Repository Layout

- [`backend/`](file:///c:/Users/agmin/Desktop/cityPulse/backend): FastAPI backend service, normalization engine, Pydantic schemas, MongoDB integration, and synthetic Jaipur municipal data.
  - See [backend/README.md](file:///c:/Users/agmin/Desktop/cityPulse/backend/README.md) for architecture, schema documentation, and API guides.

## Quick Start (Backend)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **Interactive API Docs (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Interactive API Docs (ReDoc)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
