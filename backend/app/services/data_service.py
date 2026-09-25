import json
import logging
from uuid import uuid4
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.database.connection import get_database, is_mongo_connected
from app.models.civic_event import CivicEvent, CivicEventCreate, EventSource
from app.models.common import Severity
from app.models.dashboard import (
    DashboardResponse,
    IncidentSummary,
    TrafficSummary,
    WeatherSummary,
)
from app.models.incident import (
    IncidentCreate,
    IncidentRecord,
    IncidentStatus,
    IncidentUpdate,
)
from app.models.traffic import TrafficCreate, TrafficRecord
from app.models.weather import WeatherCreate, WeatherRecord
from app.services.normalization import NormalizationService

logger = logging.getLogger("citypulse.service")

# Resolve data path robustly
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _to_mongo_doc(record) -> Dict[str, Any]:
    """
    Serialize a Pydantic model to a dict suitable for MongoDB insertion.
    - datetime fields are kept as Python datetime objects so Motor stores them
      as BSON Date (enabling proper date-range queries and index sorting).
    - Enum fields are converted to their .value strings.
    - All other fields are serialized as-is.
    """
    def _convert(obj: Any) -> Any:
        from enum import Enum as _Enum
        if isinstance(obj, _Enum):
            return obj.value
        if isinstance(obj, dict):
            return {k: _convert(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_convert(i) for i in obj]
        return obj

    raw = record.model_dump()  # mode=python: datetimes stay as datetime objects
    return _convert(raw)


class DataService:
    """
    Core Data Service for CityPulse.
    Handles data ingestion, retrieval, normalization, and dashboard aggregation.
    Works seamlessly with MongoDB when available, and transparently falls back to
    local synthetic JSON data when running standalone.
    """

    def __init__(self):
        self._memory_weather: List[WeatherRecord] = []
        self._memory_traffic: List[TrafficRecord] = []
        self._memory_incidents: List[IncidentRecord] = []
        self._memory_civic_events: List[CivicEvent] = []
        self._data_initialized: bool = False
        # Preload synthetic JSON data so service is immediately ready
        self.load_synthetic_data()

    def load_synthetic_data(self) -> None:
        """Loads synthetic JSON files into memory cache."""
        try:
            weather_path = DATA_DIR / "weather.json"
            traffic_path = DATA_DIR / "traffic.json"
            incidents_path = DATA_DIR / "incidents.json"

            if weather_path.exists():
                with open(weather_path, "r", encoding="utf-8") as f:
                    raw_w = json.load(f)
                    self._memory_weather = [WeatherRecord.model_validate(item) for item in raw_w]
            else:
                logger.warning(f"Weather data file not found at {weather_path}")

            if traffic_path.exists():
                with open(traffic_path, "r", encoding="utf-8") as f:
                    raw_t = json.load(f)
                    self._memory_traffic = [TrafficRecord.model_validate(item) for item in raw_t]
            else:
                logger.warning(f"Traffic data file not found at {traffic_path}")

            if incidents_path.exists():
                with open(incidents_path, "r", encoding="utf-8") as f:
                    raw_i = json.load(f)
                    self._memory_incidents = [IncidentRecord.model_validate(item) for item in raw_i]
            else:
                logger.warning(f"Incidents data file not found at {incidents_path}")

            # Re-generate normalized events cache
            self._rebuild_normalized_events_cache()
            self._data_initialized = True
            logger.info(
                f"Synthetic data loaded: {len(self._memory_weather)} weather records, "
                f"{len(self._memory_traffic)} traffic records, "
                f"{len(self._memory_incidents)} incidents, "
                f"{len(self._memory_civic_events)} normalized civic events."
            )

        except Exception as exc:
            logger.error(f"Error loading synthetic data: {exc}", exc_info=True)

    def _rebuild_normalized_events_cache(self) -> None:
        """Normalizes all in-memory weather, traffic, and incidents into CivicEvents."""
        events: List[CivicEvent] = []

        for w in self._memory_weather:
            events.extend(NormalizationService.normalize_weather_record(w))

        for t in self._memory_traffic:
            events.append(NormalizationService.normalize_traffic_record(t))

        for inc in self._memory_incidents:
            events.append(NormalizationService.normalize_incident_record(inc))

        # Sort descending by timestamp
        events.sort(key=lambda e: e.timestamp, reverse=True)
        self._memory_civic_events = events

    async def initialize(self) -> None:
        """Initializes service on startup; seeds MongoDB if connected and empty."""
        self.load_synthetic_data()

        if is_mongo_connected():
            db = get_database()
            if db is not None:
                try:
                    w_count = await db.weather.count_documents({})
                    if w_count == 0 and self._memory_weather:
                        await db.weather.insert_many([_to_mongo_doc(w) for w in self._memory_weather])
                        logger.info(f"Seeded MongoDB 'weather' with {len(self._memory_weather)} documents.")

                    t_count = await db.traffic.count_documents({})
                    if t_count == 0 and self._memory_traffic:
                        await db.traffic.insert_many([_to_mongo_doc(t) for t in self._memory_traffic])
                        logger.info(f"Seeded MongoDB 'traffic' with {len(self._memory_traffic)} documents.")

                    i_count = await db.incidents.count_documents({})
                    if i_count == 0 and self._memory_incidents:
                        await db.incidents.insert_many([_to_mongo_doc(i) for i in self._memory_incidents])
                        logger.info(f"Seeded MongoDB 'incidents' with {len(self._memory_incidents)} documents.")

                    c_count = await db.civic_events.count_documents({})
                    if c_count == 0 and self._memory_civic_events:
                        await db.civic_events.insert_many([_to_mongo_doc(c) for c in self._memory_civic_events])
                        logger.info(f"Seeded MongoDB 'civic_events' with {len(self._memory_civic_events)} documents.")
                except Exception as exc:
                    logger.warning(f"Failed to auto-seed MongoDB collections: {exc}")

    # ==========================================
    # WEATHER
    # ==========================================

    async def get_weather(
        self,
        zone: Optional[str] = None,
        min_rainfall: Optional[float] = None,
        condition: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> List[WeatherRecord]:
        if is_mongo_connected():
            db = get_database()
            if db is not None:
                query: Dict[str, Any] = {}
                if zone:
                    query["location.zone"] = {"$regex": f"^{zone}$", "$options": "i"}
                if min_rainfall is not None:
                    query["rainfall"] = {"$gte": min_rainfall}
                if condition:
                    query["weather_condition"] = {"$regex": condition, "$options": "i"}
                cursor = db.weather.find(query).sort("timestamp", -1).skip(skip).limit(limit)
                docs = await cursor.to_list(length=limit)
                records: List[WeatherRecord] = []
                for doc in docs:
                    try:
                        records.append(WeatherRecord.model_validate(doc))
                    except Exception as ve:
                        logger.warning(f"Skipping incompatible weather doc {doc.get('id', doc.get('_id'))}: {ve}")
                return records

        # Memory Fallback
        results = list(self._memory_weather)
        if zone:
            results = [r for r in results if r.location.zone.lower() == zone.lower()]
        if min_rainfall is not None:
            results = [r for r in results if r.rainfall >= min_rainfall]
        if condition:
            results = [r for r in results if condition.lower() in r.weather_condition.lower()]

        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[skip : skip + limit]

    async def create_weather(self, data: WeatherCreate) -> WeatherRecord:
        record_id = data.id or f"weather_jpr_{len(self._memory_weather) + 1:03d}"
        dump = data.model_dump()
        dump["id"] = record_id
        record = WeatherRecord.model_validate(dump)

        if is_mongo_connected():
            db = get_database()
            if db is not None:
                await db.weather.insert_one(_to_mongo_doc(record))

        self._memory_weather.append(record)
        # Normalize and append to civic events
        new_events = NormalizationService.normalize_weather_record(record)
        self._memory_civic_events.extend(new_events)
        self._memory_civic_events.sort(key=lambda e: e.timestamp, reverse=True)

        if is_mongo_connected():
            db = get_database()
            if db is not None and new_events:
                await db.civic_events.insert_many([_to_mongo_doc(e) for e in new_events])

        return record

    async def get_weather_by_id(self, record_id: str) -> Optional[WeatherRecord]:
        if is_mongo_connected():
            db = get_database()
            if db is not None:
                doc = await db.weather.find_one({"id": record_id})
                if doc:
                    return WeatherRecord.model_validate(doc)
        for w in self._memory_weather:
            if w.id == record_id:
                return w
        return None

    # ==========================================
    # TRAFFIC
    # ==========================================

    async def get_traffic(
        self,
        zone: Optional[str] = None,
        severity: Optional[Severity] = None,
        min_congestion: Optional[float] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> List[TrafficRecord]:
        if is_mongo_connected():
            db = get_database()
            if db is not None:
                query: Dict[str, Any] = {}
                if zone:
                    query["location.zone"] = {"$regex": f"^{zone}$", "$options": "i"}
                if severity:
                    query["severity"] = severity.value
                if min_congestion is not None:
                    query["congestion_percentage"] = {"$gte": min_congestion}
                cursor = db.traffic.find(query).sort("timestamp", -1).skip(skip).limit(limit)
                docs = await cursor.to_list(length=limit)
                records: List[TrafficRecord] = []
                for doc in docs:
                    try:
                        records.append(TrafficRecord.model_validate(doc))
                    except Exception as ve:
                        logger.warning(f"Skipping incompatible traffic doc {doc.get('id', doc.get('_id'))}: {ve}")
                return records

        results = list(self._memory_traffic)
        if zone:
            results = [r for r in results if r.location.zone.lower() == zone.lower()]
        if severity:
            results = [r for r in results if r.severity == severity]
        if min_congestion is not None:
            results = [r for r in results if r.congestion_percentage >= min_congestion]

        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[skip : skip + limit]

    async def create_traffic(self, data: TrafficCreate) -> TrafficRecord:
        record_id = data.id or f"traffic_jpr_{len(self._memory_traffic) + 1:03d}"
        dump = data.model_dump()
        dump["id"] = record_id
        record = TrafficRecord.model_validate(dump)

        if is_mongo_connected():
            db = get_database()
            if db is not None:
                await db.traffic.insert_one(_to_mongo_doc(record))

        self._memory_traffic.append(record)
        new_event = NormalizationService.normalize_traffic_record(record)
        self._memory_civic_events.append(new_event)
        self._memory_civic_events.sort(key=lambda e: e.timestamp, reverse=True)

        if is_mongo_connected():
            db = get_database()
            if db is not None:
                await db.civic_events.insert_one(_to_mongo_doc(new_event))

        return record

    async def get_traffic_by_id(self, record_id: str) -> Optional[TrafficRecord]:
        if is_mongo_connected():
            db = get_database()
            if db is not None:
                doc = await db.traffic.find_one({"id": record_id})
                if doc:
                    return TrafficRecord.model_validate(doc)
        for t in self._memory_traffic:
            if t.id == record_id:
                return t
        return None

    # ==========================================
    # INCIDENTS
    # ==========================================

    async def get_incidents(
        self,
        zone: Optional[str] = None,
        category: Optional[str] = None,
        severity: Optional[Severity] = None,
        status: Optional[IncidentStatus] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> List[IncidentRecord]:
        if not is_mongo_connected():
            return []
        if is_mongo_connected():
            db = get_database()
            if db is not None:
                query: Dict[str, Any] = {}
                for required_field in ("id", "incident_category", "description", "severity", "location", "timestamp"):
                    query[required_field] = {"$exists": True}
                if zone:
                    query["location.zone"] = {"$regex": f"^{zone}$", "$options": "i"}
                if category:
                    query["incident_category"] = category
                if severity:
                    query["severity"] = severity.value
                if status:
                    query["status"] = status.value
                cursor = db.incidents.find(query).sort("timestamp", -1).skip(skip).limit(limit)
                docs = await cursor.to_list(length=limit)
                records: List[IncidentRecord] = []
                for doc in docs:
                    try:
                        records.append(IncidentRecord.model_validate(doc))
                    except Exception as ve:
                        logger.warning(f"Skipping incompatible incident doc {doc.get('id', doc.get('_id'))}: {ve}")
                # If MongoDB had documents but none passed validation (stale schema),
                # return only valid database records. A connected MongoDB read must
                # never silently replace invalid/empty persisted data with demo rows.
                if docs and not records:
                    logger.warning(
                        f"MongoDB incidents: {len(docs)} docs fetched but 0 valid. "
                        "Returning an empty valid-record set; no synthetic fallback used."
                    )
                return records

        results = list(self._memory_incidents)
        if zone:
            results = [r for r in results if r.location.zone.lower() == zone.lower()]
        if category:
            results = [r for r in results if r.incident_category.value.lower() == category.lower()]
        if severity:
            results = [r for r in results if r.severity == severity]
        if status:
            results = [r for r in results if r.status == status]

        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[skip : skip + limit]

    async def create_incident(self, data: IncidentCreate) -> IncidentRecord:
        record_id = data.id or f"inc_jpr_{uuid4().hex[:12]}"
        dump = data.model_dump()
        dump["id"] = record_id
        record = IncidentRecord.model_validate(dump)

        if is_mongo_connected():
            db = get_database()
            if db is not None:
                document = _to_mongo_doc(record)
                await db.incidents.insert_one(document)

        self._memory_incidents.append(record)
        new_event = NormalizationService.normalize_incident_record(record)
        self._memory_civic_events.append(new_event)
        self._memory_civic_events.sort(key=lambda e: e.timestamp, reverse=True)

        if is_mongo_connected():
            db = get_database()
            if db is not None:
                await db.civic_events.insert_one(_to_mongo_doc(new_event))

        return record

    async def get_incident_by_id(self, incident_id: str) -> Optional[IncidentRecord]:
        if is_mongo_connected():
            db = get_database()
            if db is not None:
                doc = await db.incidents.find_one({"id": incident_id})
                if doc:
                    return IncidentRecord.model_validate(doc)
        for inc in self._memory_incidents:
            if inc.id == incident_id:
                return inc
        return None

    async def update_incident(
        self, incident_id: str, data: IncidentUpdate
    ) -> Optional[IncidentRecord]:
        update_fields = data.model_dump(exclude_unset=True)
        if not update_fields:
            return await self.get_incident_by_id(incident_id)

        target_inc: Optional[IncidentRecord] = None
        target_idx: int = -1
        for idx, inc in enumerate(self._memory_incidents):
            if inc.id == incident_id:
                target_inc = inc
                target_idx = idx
                break

        if target_inc is None and not is_mongo_connected():
            return None

        if is_mongo_connected():
            db = get_database()
            if db is not None:
                await db.incidents.update_one({"id": incident_id}, {"$set": update_fields})
                doc = await db.incidents.find_one({"id": incident_id})
                if doc:
                    target_inc = IncidentRecord.model_validate(doc)

        if target_inc is not None and target_idx >= 0:
            current_dict = target_inc.model_dump()
            current_dict.update(update_fields)
            target_inc = IncidentRecord.model_validate(current_dict)
            self._memory_incidents[target_idx] = target_inc

        if target_inc:
            self._rebuild_normalized_events_cache()
            if is_mongo_connected():
                db = get_database()
                if db is not None:
                    updated_event = NormalizationService.normalize_incident_record(target_inc)
                    await db.civic_events.update_one(
                        {"id": f"{incident_id}_event"},
                        {"$set": updated_event.model_dump(mode="json")},
                        upsert=True,
                    )
            return target_inc

        return None

    # ==========================================
    # CIVIC EVENTS (NORMALIZED)
    # ==========================================

    async def get_civic_events(
        self,
        source: Optional[EventSource] = None,
        event_type: Optional[str] = None,
        zone: Optional[str] = None,
        severity: Optional[Severity] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> List[CivicEvent]:
        if is_mongo_connected():
            db = get_database()
            if db is not None:
                query: Dict[str, Any] = {}
                if source:
                    query["source"] = source.value
                if event_type:
                    query["type"] = event_type
                if zone:
                    query["zone"] = {"$regex": f"^{zone}$", "$options": "i"}
                if severity:
                    query["severity"] = severity.value
                cursor = db.civic_events.find(query).sort("timestamp", -1).skip(skip).limit(limit)
                docs = await cursor.to_list(length=limit)
                events: List[CivicEvent] = []
                for doc in docs:
                    try:
                        events.append(CivicEvent.model_validate(doc))
                    except Exception as ve:
                        logger.warning(f"Skipping incompatible civic_event doc {doc.get('id', doc.get('_id'))}: {ve}")
                return events

        results = list(self._memory_civic_events)
        if source:
            results = [r for r in results if r.source == source]
        if event_type:
            results = [r for r in results if r.type.lower() == event_type.lower()]
        if zone:
            results = [r for r in results if r.zone.lower() == zone.lower()]
        if severity:
            results = [r for r in results if r.severity == severity]

        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[skip : skip + limit]

    async def get_civic_event_by_id(self, event_id: str) -> Optional[CivicEvent]:
        if is_mongo_connected():
            db = get_database()
            if db is not None:
                doc = await db.civic_events.find_one({"id": event_id})
                if doc:
                    return CivicEvent.model_validate(doc)
        for ev in self._memory_civic_events:
            if ev.id == event_id:
                return ev
        return None

    async def create_civic_event(self, data: CivicEventCreate) -> CivicEvent:
        event_id = data.id or f"civic_ev_{len(self._memory_civic_events) + 1:04d}"
        dump = data.model_dump()
        dump["id"] = event_id
        if dump.get("timestamp") is None:
            dump["timestamp"] = datetime.now(timezone.utc)
        record = CivicEvent.model_validate(dump)

        if is_mongo_connected():
            db = get_database()
            if db is not None:
                await db.civic_events.insert_one(_to_mongo_doc(record))

        self._memory_civic_events.insert(0, record)
        return record

    # ==========================================
    # DASHBOARD AGGREGATION
    # ==========================================

    async def get_dashboard_summary(self, live_weather_records: Optional[List[WeatherRecord]] = None) -> DashboardResponse:
        """
        Aggregates multi-source telemetry into the conceptual dashboard response.
        Computes civic health score, summaries, active alerts, and recent events.
        Leaves anomaly, correlation, and summary placeholders ready for future ML.
        """
        weather_records = live_weather_records if live_weather_records is not None else await self.get_weather(limit=100)
        traffic_records = await self.get_traffic(limit=100)
        incident_records = await self.get_incidents(limit=100)
        civic_events = await self.get_civic_events(limit=50)

        # 1. Weather Summary
        if weather_records:
            avg_temp = round(sum(w.temperature for w in weather_records) / len(weather_records), 1)
            avg_rain = round(sum(w.rainfall for w in weather_records) / len(weather_records), 1)
            max_rain = round(max(w.rainfall for w in weather_records), 1)
            avg_humidity = round(sum(w.humidity for w in weather_records) / len(weather_records), 1)
            conditions = [w.weather_condition for w in weather_records]
            dominant_condition = Counter(conditions).most_common(1)[0][0] if conditions else "Clear"
            active_rain_zones = sorted(list({w.location.zone for w in weather_records if w.rainfall > 0}))
            reporting_count = len({w.location.zone for w in weather_records})
        else:
            avg_temp = avg_rain = max_rain = avg_humidity = None
            dominant_condition = None
            active_rain_zones = []
            reporting_count = 0

        weather_summary = WeatherSummary(
            average_temperature=avg_temp,
            average_rainfall=avg_rain,
            max_rainfall=max_rain,
            dominant_condition=dominant_condition,
            average_humidity=avg_humidity,
            active_rain_zones=active_rain_zones,
            total_reporting_stations=reporting_count,
        )

        # 2. Traffic Summary
        if traffic_records:
            avg_congestion = round(sum(t.congestion_percentage for t in traffic_records) / len(traffic_records), 1)
            avg_delay = round(sum(t.delay for t in traffic_records) / len(traffic_records), 1)

            # Find worst corridor
            sorted_by_cong = sorted(traffic_records, key=lambda t: t.congestion_percentage, reverse=True)
            worst_traffic = sorted_by_cong[0]
            most_congested_corridor = worst_traffic.location.road_name or worst_traffic.location.landmark or "Tonk Road"
            most_congested_zone = worst_traffic.location.zone

            severe_count = sum(1 for t in traffic_records if t.severity in [Severity.HIGH, Severity.CRITICAL])
            severity_counts = Counter(t.severity.value for t in traffic_records)
        else:
            avg_congestion, avg_delay = 0.0, 0.0
            most_congested_corridor = None
            most_congested_zone = None
            severe_count = 0
            severity_counts = {}

        traffic_summary = TrafficSummary(
            average_congestion=avg_congestion,
            average_delay_minutes=avg_delay,
            most_congested_corridor=most_congested_corridor,
            most_congested_zone=most_congested_zone,
            severe_congestion_corridors_count=severe_count,
            congestion_breakdown_by_severity=dict(severity_counts),
        )

        # 3. Incident Summary
        total_inc = len(incident_records)
        active_inc = sum(1 for inc in incident_records if inc.status != IncidentStatus.RESOLVED)
        resolved_inc = sum(1 for inc in incident_records if inc.status == IncidentStatus.RESOLVED)
        critical_inc = sum(
            1 for inc in incident_records if inc.severity == Severity.CRITICAL and inc.status != IncidentStatus.RESOLVED
        )

        cat_counts = Counter(inc.incident_category.value for inc in incident_records)
        inc_sev_counts = Counter(inc.severity.value for inc in incident_records)

        incident_summary = IncidentSummary(
            total_incidents=total_inc,
            active_incidents=active_inc,
            resolved_incidents=resolved_inc,
            critical_incidents=critical_inc,
            breakdown_by_category=dict(cat_counts),
            breakdown_by_severity=dict(inc_sev_counts),
        )

        # 4. Civic Health Score Calculation
        # Baseline = 100
        # Penalties:
        # - Traffic congestion penalty: up to -25 pts
        # - Active incidents penalty: -6 per critical, -3 per high, -1 per medium (up to -30 pts)
        # - Weather severity penalty: up to -15 pts
        # Stored traffic rows are development seed observations, not a live feed.
        # Do not let them affect a score presented as a current city status.
        traffic_penalty = 0.0
        incident_penalty = 0.0
        for inc in incident_records:
            if inc.status != IncidentStatus.RESOLVED:
                if inc.severity == Severity.CRITICAL:
                    incident_penalty += 6.0
                elif inc.severity == Severity.HIGH:
                    incident_penalty += 3.0
                elif inc.severity == Severity.MEDIUM:
                    incident_penalty += 1.0
        incident_penalty = min(35.0, incident_penalty)

        weather_penalty = 0.0
        if max_rain is not None and max_rain >= 40.0:
            weather_penalty = 12.0
        elif max_rain is not None and max_rain >= 20.0:
            weather_penalty = 6.0
        elif max_rain is not None and max_rain >= 5.0:
            weather_penalty = 2.0

        computed_score = int(round(max(10.0, min(100.0, 100.0 - (traffic_penalty + incident_penalty + weather_penalty)))))

        # 5. Active Alerts (CivicEvents with High or Critical severity)
        alerts: List[CivicEvent] = [
            e for e in civic_events if e.severity in [Severity.HIGH, Severity.CRITICAL]
        ]
        # Keep top 8 distinct urgent alerts
        dedup_alerts: List[CivicEvent] = []
        seen_keys = set()
        for a in alerts:
            k = (a.source, a.type, a.zone)
            if k not in seen_keys:
                seen_keys.add(k)
                dedup_alerts.append(a)
            if len(dedup_alerts) >= 8:
                break

        # 6. Latest 10 Events
        latest_events = civic_events[:10]

        return DashboardResponse(
            healthScore=computed_score,
            city="Jaipur",
            timestamp=datetime.now(timezone.utc),
            weather=weather_summary,
            traffic=traffic_summary,
            incidents=incident_summary,
            alerts=dedup_alerts,
            latestEvents=latest_events,
            anomalies=[],
            correlations=[],
            summary=None,
            data_sources={
                "weather": (
                    "Cached Open-Meteo weather · " + (weather_records[0].warning or "last successful observation")
                    if weather_records and weather_records[0].is_stale
                    else "Live · Open-Meteo forecast model" if weather_records
                    else "Unavailable · Open-Meteo could not provide current weather"
                ),
                "traffic": "Development/stored observations · no live traffic provider configured",
                "incidents": "MongoDB user-reported records · not independently verified" if is_mongo_connected() else "Unavailable · MongoDB disconnected",
                "crowd_prediction": "Existing model · trained on synthetic development labels; not real-world validated",
            },
        )


data_service = DataService()
