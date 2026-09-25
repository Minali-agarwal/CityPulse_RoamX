# CityPulse — Live Civic Health Dashboard (Backend)

CityPulse is a civic health monitoring and situational intelligence backend. It aggregates and normalizes heterogeneous civic telemetry across three primary municipal pillars:

1. **Weather** (meteorological sensor telemetry, rainfall intensity, humidity, air quality)
2. **Traffic** (road corridor congestion, vehicular delay, speeds, choke points)
3. **Civic Incidents** (waterlogging, road accidents, road damage, fallen trees, streetlight outages)

All data streams are transformed into a unified **CivicEvent** common schema, enabling multi-source cross-correlation, anomaly detection readiness, and automated city-wide **Civic Health Scoring** (0–100). The current demonstration dataset models a severe monsoon rain event across key zones of **Jaipur, Rajasthan, India** (Malviya Nagar, Sanganer, Pink City, C-Scheme, Mansarovar, Vaishali Nagar).

---

## Technology Stack

- **Runtime & Language**: Python 3.11+ / Python 3.13
- **Framework**: FastAPI (high-performance asynchronous REST API)
- **Data Validation & Schemas**: Pydantic v2 & `pydantic-settings`
- **Database & Persistence**: MongoDB via Motor (async driver) with zero-config in-memory fallback to local synthetic JSON data
- **ASGI Web Server**: Uvicorn
- **Testing & Verification**: Pytest & HTTPX (ASGI in-memory transport)

---

## Folder Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app factory, CORS, lifecycle & exception handlers
│   ├── config.py                # Environment configuration via Pydantic BaseSettings
│   ├── models/
│   │   ├── __init__.py
│   │   ├── common.py            # Location, coordinates & Severity enums
│   │   ├── weather.py           # WeatherBase, WeatherRecord, WeatherCreate schemas
│   │   ├── traffic.py           # TrafficBase, TrafficRecord, TrafficCreate schemas
│   │   ├── incident.py          # IncidentBase, IncidentRecord, IncidentCreate, IncidentUpdate schemas
│   │   ├── civic_event.py       # Normalized CivicEvent & CivicEventCreate schemas
│   │   └── dashboard.py         # Aggregation summary models & DashboardResponse
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── weather.py           # Weather observations API (/api/weather)
│   │   ├── traffic.py           # Traffic congestion & delay API (/api/traffic)
│   │   ├── incidents.py         # Municipal incident reports & status API (/api/incidents)
│   │   ├── civic_events.py      # Normalized cross-domain telemetry API (/api/civic-events)
│   │   └── dashboard.py         # Aggregated civic health snapshot API (/api/dashboard)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── normalization.py     # Cross-domain normalization logic -> CivicEvent
│   │   └── data_service.py      # Core data ingestion, filtering, aggregation & MongoDB/fallback store
│   ├── database/
│   │   ├── __init__.py
│   │   └── connection.py        # Motor MongoDB connection manager & graceful synthetic fallback
│   └── utils/
│       ├── __init__.py
│       └── geo.py               # Haversine distance & spatial calculations
├── data/
│   ├── weather.json             # Synthetic weather sensor observations (Jaipur)
│   ├── traffic.json             # Synthetic traffic corridor telemetry (Jaipur)
│   └── incidents.json           # Synthetic municipal incident reports (Jaipur)
├── tests/
│   ├── test_api.py              # End-to-end endpoint & validation error tests
│   └── test_normalization.py    # Unit tests for domain normalization logic
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment configuration template
├── .env                         # Local development environment configuration
└── README.md                    # Project documentation
```

---

## Installation & Setup

### 1. Prerequisites
- Python 3.10 or higher (Python 3.11, 3.12, 3.13 tested)
- (Optional) MongoDB local service or MongoDB Atlas cluster. *If MongoDB is not running, the application will automatically fall back to local synthetic JSON data without any crashes or degraded functionality.*

### 2. Install Dependencies
From the `backend/` directory:
```bash
cd backend
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
Default `.env` configuration:
```ini
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=citypulse
MONGODB_CONNECT_TIMEOUT_MS=1500
USE_SYNTHETIC_DATA_FALLBACK=True

HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1:8000
```

---

## How to Run the Server

Start the development server with auto-reload:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Or run directly with Python:
```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

When started, access:
- **Interactive Swagger Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Interactive Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI JSON Schema**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)
- **Health Check Endpoint**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

## Normalized CivicEvent Schema

The `CivicEvent` schema is the common data contract across all municipal domains. It allows heterogeneous data (a millimeter rainfall reading, a traffic congestion percentage, or a waterlogging incident report) to be represented in a single format for spatial queries, map overlays, anomaly detection, and ML clustering.

### Schema Definition:
| Field | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `id` | `string` | Unique event ID | `"weather_jpr_001_rainfall"` |
| `source` | `enum` | Domain origin (`weather`, `traffic`, `incident`) | `"weather"` |
| `type` | `string` | Specific metric type (e.g. `rainfall`, `congestion`, `waterlogging`) | `"rainfall"` |
| `value` | `float \| int \| string \| null` | Normalized scalar reading or count | `32.0` |
| `unit` | `string \| null` | Unit of measure (`mm`, `°C`, `%`, `mins`, `incident`) | `"mm"` |
| `latitude` | `float` | WGS84 latitude coordinate (-90 to 90) | `26.8530` |
| `longitude`| `float` | WGS84 longitude coordinate (-180 to 180) | `75.8150` |
| `zone` | `string` | Civic zone or administrative sector | `"Malviya Nagar"` |
| `timestamp`| `datetime` | ISO 8601 UTC timestamp | `"2026-09-24T15:00:00Z"` |
| `severity` | `enum` | Normalized severity level (`low`, `medium`, `high`, `critical`)| `"critical"` |
| `metadata` | `object` | Raw telemetry and source-specific context | `{"humidity": 88, "landmark": "GT"}` |

---

## API Endpoints List

### 1. System & Health
- `GET /api/health` — System status, database engine, active data source, demonstration city, uptime.
- `GET /` — API root index with route map and documentation links.

### 2. Dashboard Aggregation
- `GET /api/dashboard` — Unified civic health summary:
  - `healthScore` (0–100 integer)
  - `weather` (averages, dominant condition, active rain zones)
  - `traffic` (average congestion, delay, most congested corridor)
  - `incidents` (total, active, critical, category breakdown)
  - `alerts` (active high/critical civic events)
  - `latestEvents` (most recent 10 normalized events)
  - `anomalies` (placeholder for ML pipeline; returns `[]`)
  - `correlations` (placeholder for ML pipeline; returns `[]`)
  - `summary` (placeholder for LLM summary; returns `null`)

### 3. Weather
- `GET /api/weather` — Query observations. Query params: `zone`, `min_rainfall`, `condition`, `limit`, `skip`.
- `GET /api/weather/{record_id}` — Retrieve a specific weather observation by ID.
- `POST /api/weather` — Ingest new meteorological reading (auto-normalizes to `CivicEvent`).

### 4. Traffic
- `GET /api/traffic` — Query traffic corridor conditions. Query params: `zone`, `severity`, `min_congestion`, `limit`, `skip`.
- `GET /api/traffic/{record_id}` — Retrieve a specific traffic corridor reading by ID.
- `POST /api/traffic` — Ingest new traffic observation (auto-normalizes to `CivicEvent`).

### 5. Civic Incidents
- `GET /api/incidents` — Query incidents. Query params: `zone`, `category`, `severity`, `status`, `limit`, `skip`.
- `GET /api/incidents/{incident_id}` — Retrieve a specific incident by ID.
- `POST /api/incidents` — Report a new civic incident (auto-normalizes to `CivicEvent`).
- `PATCH /api/incidents/{incident_id}` — Update incident status (`reported` -> `in_progress` -> `resolved`), severity, description, or clearance estimate.

### 6. Normalized Civic Events
- `GET /api/civic-events` — Query unified events. Query params: `source`, `type`, `zone`, `severity`, `limit`, `skip`.
- `GET /api/civic-events/{event_id}` — Retrieve a specific normalized event by ID.
- `POST /api/civic-events` — Directly ingest a pre-normalized civic event.

---

## Example API Responses

### 1. `GET /api/health`
```json
{
  "status": "healthy",
  "service": "CityPulse Backend",
  "version": "1.0.0",
  "environment": "development",
  "database": {
    "connected": false,
    "engine": "None",
    "activeDataSource": "Local Synthetic JSON Data"
  },
  "demonstrationCity": "Jaipur, Rajasthan, India",
  "uptimeSeconds": 14.82,
  "timestamp": "2026-09-24T16:15:00.000000Z"
}
```

### 2. `GET /api/dashboard`
```json
{
  "healthScore": 68,
  "city": "Jaipur",
  "timestamp": "2026-09-24T16:15:00.000000Z",
  "weather": {
    "average_temperature": 29.4,
    "average_rainfall": 17.6,
    "max_rainfall": 48.0,
    "dominant_condition": "Heavy Rain",
    "average_humidity": 86.2,
    "active_rain_zones": ["C-Scheme", "Malviya Nagar", "Mansarovar", "Sanganer"],
    "total_reporting_stations": 6
  },
  "traffic": {
    "average_congestion": 74.8,
    "average_delay_minutes": 23.5,
    "most_congested_corridor": "Tonk Road Corridor",
    "most_congested_zone": "Sanganer",
    "severe_congestion_corridors_count": 5,
    "congestion_breakdown_by_severity": {
      "critical": 3,
      "high": 3,
      "medium": 2
    }
  },
  "incidents": {
    "total_incidents": 8,
    "active_incidents": 6,
    "resolved_incidents": 2,
    "critical_incidents": 2,
    "breakdown_by_category": {
      "waterlogging": 4,
      "road_accident": 2,
      "traffic_signal_failure": 1,
      "fallen_tree": 1
    },
    "breakdown_by_severity": {
      "critical": 2,
      "high": 3,
      "medium": 2,
      "low": 1
    }
  },
  "alerts": [
    {
      "id": "inc_jpr_001_event",
      "source": "incident",
      "type": "waterlogging",
      "value": 1.0,
      "unit": "incident",
      "latitude": 26.8220,
      "longitude": 75.7950,
      "zone": "Sanganer",
      "timestamp": "2026-09-24T15:15:00+05:30",
      "severity": "critical",
      "metadata": {
        "description": "Severe waterlogging under Durgapura flyover, 2.5 ft water depth.",
        "status": "in_progress"
      }
    }
  ],
  "latestEvents": [ ... ],
  "anomalies": [],
  "correlations": [],
  "summary": null
}
```

### 3. `GET /api/civic-events?source=incident&severity=critical`
```json
[
  {
    "id": "inc_jpr_001_event",
    "source": "incident",
    "type": "waterlogging",
    "value": 1.0,
    "unit": "incident",
    "latitude": 26.8220,
    "longitude": 75.7950,
    "zone": "Sanganer",
    "timestamp": "2026-09-24T15:15:00+05:30",
    "severity": "critical",
    "metadata": {
      "raw_id": "inc_jpr_001",
      "status": "in_progress",
      "description": "Severe waterlogging under Durgapura flyover, 2.5 ft water depth blocking lower carriageway.",
      "reported_by": "Traffic Police Control Room",
      "estimated_clearance_minutes": 60,
      "landmark": "Durgapura Flyover Underpass",
      "road_name": "Tonk Road"
    }
  }
]
```

---

## Running the Automated Test Suite

Run all tests offline using the in-memory ASGI client:
```bash
python -m pytest tests/ -v
```
To run specific test modules:
```bash
python -m pytest tests/test_api.py -v
python -m pytest tests/test_normalization.py -v
```
