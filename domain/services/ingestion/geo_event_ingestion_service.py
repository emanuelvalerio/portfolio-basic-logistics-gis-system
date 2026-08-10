"""
Serviço de ingestão de eventos geoespaciais
============================================

Consome um SourceConnector (ex.: SipamFogoConnector) e grava/atualiza os
eventos na tabela `geo_events`, seguindo o padrão do projeto:

  1. Garante a extensão PostGIS e a tabela (Base.metadata.create_all).
  2. Converte a geometria: GeoJSON (dict) -> shapely -> valor do PostGIS
     via geoalchemy2.shape.from_shape(..., srid=4326).
  3. Faz UPSERT idempotente (ON CONFLICT (source, external_id) DO UPDATE),
     de modo que reingerir a mesma fonte atualiza em vez de duplicar.

Local sugerido:
    domain/services/ingestion/geo_event_ingestion_service.py
"""

from __future__ import annotations

from shapely.geometry import shape
from geoalchemy2.shape import from_shape
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from domain.config.database_config import Base, engine, SessionLocal
from domain.repositories.data_ingestion.geo_event import GeoEvent
from .source_connector import SourceConnector


class GeoEventIngestionService:

    def _ensure_schema(self) -> None:
        """Garante o PostGIS e a tabela geo_events (mesmo padrão create_all do projeto)."""
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        except Exception:
            # PostGIS provavelmente já está habilitado (imagem kartoza/postgis).
            pass
        Base.metadata.create_all(bind=engine)

    def ingest(self, connector: SourceConnector) -> dict:
        self._ensure_schema()

        session = SessionLocal()
        processed = 0
        try:
            for dto in connector.fetch():
                if not dto.geometry:
                    continue

                # GeoJSON -> shapely -> valor do PostGIS (SRID 4326).
                # As coordenadas do SIPAM vêm em SIRGAS 2000 (4674), que no Brasil
                # é ~coincidente com o WGS84 (4326); tratamos como 4326 aqui.
                geom = from_shape(shape(dto.geometry), srid=4326)

                stmt = insert(GeoEvent).values(
                    source=dto.source,
                    external_id=dto.external_id,
                    event_type=dto.event_type,
                    occurred_at=dto.occurred_at,
                    geom=geom,
                    properties=dto.properties,
                )
                # Upsert: se (source, external_id) já existe, atualiza.
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_geo_event_source_ext_id",
                    set_={
                        "event_type": stmt.excluded.event_type,
                        "occurred_at": stmt.excluded.occurred_at,
                        "geom": stmt.excluded.geom,
                        "properties": stmt.excluded.properties,
                    },
                )
                session.execute(stmt)
                processed += 1

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        return {
            "source": connector.source,
            "event_type": connector.event_type,
            "processed": processed,
        }
