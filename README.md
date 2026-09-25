# CityPulse

### A Smart Civic Intelligence Platform for Jaipur

CityPulse is a civic intelligence and city-monitoring platform designed to bring important urban information into one unified dashboard.

It combines weather information, traffic events, citizen-reported incidents, crowd prediction, recommendations, notifications, reports, and an interactive city map to provide a clearer picture of the current city situation.

The goal of CityPulse is to help citizens and city administrators understand what is happening across the city and make better-informed decisions using available data.

---

## Features

### 1. City Health Dashboard

The dashboard provides a quick overview of the current civic condition of the city.

It includes:

- City health score
- Active incidents
- Reporting zones
- Weather condition
- Traffic information
- Crowd prediction
- Recent civic alerts
- Data source indicators

---

### 2. Weather Monitoring

CityPulse integrates weather information through the Open-Meteo weather service.

The weather section provides:

- Current weather information
- Temperature
- Weather conditions
- Weather-related indicators
- Data refresh functionality
- Weather information used by other dashboard components

Weather data is retrieved from an external weather provider when the service is available.

---

### 3. Traffic Monitoring

The traffic section provides information about traffic events and congestion.

It includes:

- Traffic events
- Congestion information
- Location-based traffic information
- Traffic indicators on the city map
- Traffic-related civic alerts

The currently stored traffic dataset is development data and is clearly identified as non-live data.

---

### 4. Citizen Incident Reporting

Citizens can report civic problems such as:

- Waterlogging
- Road accidents
- Road damage
- Garbage-related issues
- Other civic incidents

Each report can contain relevant information such as:

- Incident type
- Location
- Description
- Severity
- Timestamp
- Status

Submitted incidents are stored in MongoDB when the database is available.

---

### 5. Incident and Report Management

The Reports section provides a centralized view of reported civic incidents.

Users can:

- View reported incidents
- View incident details
- Filter incidents
- Check incident status
- Refresh reports
- Track reported civic problems

Incident information is connected to the backend data service.

---

### 6. Crowd Prediction

CityPulse includes a machine-learning based crowd prediction feature.

The system predicts crowd levels such as:

- Low
- Moderate
- High

It also provides:

- Prediction confidence
- Prediction timestamp
- Location
- Prediction information
- AI-generated insights based on available prediction data

The current development model is trained using synthetic/demo observations and should not be considered a validated real-world crowd forecasting system.

---

### 7. Civic Alerts and Notifications

CityPulse provides notifications for important civic events.

Examples include:

- Traffic congestion
- Waterlogging
- Road accidents
- Other reported incidents

Users can interact with notifications through:

- View notification
- Mark as read
- Remove notification
- View all notifications
- Refresh notification data

---

### 8. Live City Map

The map provides a visual representation of civic events across Jaipur.

It can display:

- Incident markers
- Traffic markers
- Weather-related markers when available
- Event locations
- Civic activity areas

The map connects backend event information with geographic coordinates to provide a city-level visual overview.

---

### 9. Smart Recommendations

CityPulse contains a recommendation layer that uses available city information to generate contextual recommendations.

Recommendations can consider information such as:

- Weather conditions
- Traffic events
- Reported incidents
- Crowd predictions

The recommendation system is designed to demonstrate how multiple city data sources can be combined into actionable information.

---

## System Architecture

CityPulse follows a frontend-backend architecture.

```text
                    ┌─────────────────────┐
                    │      CityPulse      │
                    │     Frontend UI     │
                    └──────────┬──────────┘
                               │
                               │ HTTP / REST API
                               ▼
                    ┌─────────────────────┐
                    │     FastAPI         │
                    │      Backend        │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
       ┌───────────┐     ┌────────────┐    ┌─────────────┐
       │ MongoDB   │     │ External   │    │ ML Service  │
       │           │     │ Weather API│    │             │
       └───────────┘     └────────────┘    └─────────────┘
             │                 │                 │
             ▼                 ▼                 ▼
        Incidents          Weather         Crowd Prediction
        Reports            Data            Model
```

## Technology Stack

### Frontend
   - HTML5
   - CSS3
   - JavaScript
   - Responsive UI
   - REST API integration

### Backend
   - Python
   -FastAPI
   - Uvicorn
   - Pydantic
   - Motor
   - MongoDB

### Machine Learning
   - Python
   - Scikit-learn
   - Joblib
   - Pandas
   - NumPy

### External Data
   - Open-Meteo for weather information

### Database
   - MongoDB Atlas


## Project Structure

```text
CityPulse/
│
├── backend/
│   ├── app/
│   │   ├── database/
│   │   │   ├── connection.py
│   │   │   └── indexes.py
│   │   │
│   │   ├── models/
│   │   │   ├── civic_event.py
│   │   │   ├── common.py
│   │   │   ├── crowd_prediction.py
│   │   │   ├── dashboard.py
│   │   │   ├── incident.py
│   │   │   ├── traffic.py
│   │   │   └── weather.py
│   │   │
│   │   ├── routes/
│   │   │   ├── civic_events.py
│   │   │   ├── crowd_prediction.py
│   │   │   ├── dashboard.py
│   │   │   ├── incidents.py
│   │   │   ├── recommendations.py
│   │   │   ├── traffic.py
│   │   │   └── weather.py
│   │   │
│   │   ├── services/
│   │   │   ├── crowd_prediction.py
│   │   │   ├── data_service.py
│   │   │   ├── live_weather.py
│   │   │   ├── normalization.py
│   │   │   └── recommendations.py
│   │   │
│   │   ├── utils/
│   │   │   └── geo.py
│   │   │
│   │   ├── config.py
│   │   └── main.py
│   │
│   ├── data/
│   │   ├── incidents.json
│   │   ├── traffic.json
│   │   └── weather.json
│   │
│   ├── tests/
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   └── package-lock.json
│
├── ml/
│   ├── artifacts/
│   │   ├── crowd_level_model.joblib
│   │   ├── crowd_level_preprocessor.joblib
│   │   └── training_metrics.json
│   │
│   ├── data/
│   │   ├── crowd_observations.csv
│   │   └── crowd_observations_TEMPLATE_DEV_ONLY.csv
│   │
│   ├── data_pipeline.py
│   ├── train.py
│   ├── requirements.txt
│   └── README.md
│
├── .gitignore
└── README.md

```

## Data Sources

CityPulse uses multiple sources of information.

| Data | Source | Status |
| --- | --- | --- |
| Weather | Open-Meteo | External/live provider when available |
| Incidents | MongoDB | User-reported data |
| Traffic | Backend development dataset | Non-live development data |
| Crowd Prediction | ML model | Synthetic/demo training data |
| Recommendations | CityPulse backend | Derived from available data |

### Data Transparency

CityPulse intentionally displays data provenance to distinguish between external/live information, user-reported information, and development/demo datasets.

This prevents development data from being presented as verified real-world information.

---

## Production Vision

The long-term vision of CityPulse is to become a centralized civic intelligence platform.

Instead of simply displaying data, the platform can continuously:

```text
Collect Data
     ↓
Validate Data
     ↓
Normalize Data
     ↓
Analyze Data
     ↓
Predict Conditions
     ↓
Generate Recommendations
     ↓
Notify Users
     ↓
Support Civic Decision Making

```


