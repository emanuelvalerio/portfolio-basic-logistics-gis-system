"""
Modelo de domínio: GeoEvent
============================

Evento geoespacial NORMALIZADO, proveniente de qualquer fonte externa
(incêndio, segurança hídrica, desmatamento, etc.).

Esquema comum (mesma tabela para todas as fontes) — é o que permite o
CRUZAMENTO de informações via consultas espaciais no PostGIS.

Local sugerido:
    domain/repositories/data_ingestion/geo_event.py
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry

from domain.config.database_config import Base


class GeoEvent(Base):
    __tablename__ = "geo_events"

    id = Column(Integer, primary_key=True)

    # --- Procedência ---
    source = Column(String(64), nullable=False, index=True)        # 'sipam_fogo', 'snirh', ...
    external_id = Column(String(128), nullable=False)              # id do evento NA FONTE (idempotência)
    event_type = Column(String(64), nullable=False, index=True)    # 'incendio', 'seguranca_hidrica', ...

    # --- Quando ocorreu na fonte ---
    occurred_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # --- Geometria em WGS84 (SRID 4326): aceita ponto, linha OU polígono ---
    # O GeoAlchemy2 cria o índice espacial GiST automaticamente (spatial_index=True).
    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326), nullable=False)

    # --- Atributos originais da fonte (auditabilidade + enriquecimento futuro) ---
    properties = Column(JSONB, nullable=False, default=dict)

    # --- Controle de ingestão ---
    ingested_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        # Idempotência: a mesma ocorrência da mesma fonte nunca duplica (permite upsert).
        UniqueConstraint("source", "external_id", name="uq_geo_event_source_ext_id"),
    )

    def __repr__(self) -> str:
        return f"<GeoEvent {self.source}:{self.external_id} ({self.event_type})>"
