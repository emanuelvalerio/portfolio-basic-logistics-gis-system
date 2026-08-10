"""
Serviço de consulta de eventos geoespaciais
============================================

Lê a tabela `geo_events` e devolve um GeoJSON FeatureCollection — o mesmo
formato que o frontend já consome nos outros `get-...-from-db`.

Usa ST_AsGeoJSON (PostGIS) para converter a geometria. Não depende de
`requests`/`shapely`, então é seguro importar no boot da API.

Local sugerido:
    domain/services/ingestion/geo_event_query_service.py
"""

from __future__ import annotations

import json
from typing import Optional

from sqlalchemy import select, func

from domain.config.database_config import SessionLocal
from domain.repositories.data_ingestion.geo_event import GeoEvent


class QueryGeoEventsService:
    def __init__(self, event_type: Optional[str] = None, limit: int = 2000):
        self.event_type = event_type
        self.limit = limit

    def execute(self) -> dict:
        session = SessionLocal()
        try:
            stmt = select(
                GeoEvent.external_id,
                GeoEvent.event_type,
                GeoEvent.occurred_at,
                GeoEvent.properties,
                func.ST_AsGeoJSON(GeoEvent.geom).label("geojson"),
            )
            if self.event_type:
                stmt = stmt.where(GeoEvent.event_type == self.event_type)
            stmt = stmt.limit(self.limit)

            features = []
            for row in session.execute(stmt):
                features.append(
                    {
                        "type": "Feature",
                        "geometry": json.loads(row.geojson) if row.geojson else None,
                        "properties": {
                            "external_id": row.external_id,
                            "event_type": row.event_type,
                            "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
                            **(row.properties or {}),
                        },
                    }
                )

            return {"type": "FeatureCollection", "features": features}
        finally:
            session.close()
