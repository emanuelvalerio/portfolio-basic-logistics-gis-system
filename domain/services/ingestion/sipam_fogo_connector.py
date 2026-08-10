"""
Conector do Painel do Fogo (SIPAM) — eventos de incêndio via GeoServer WFS
==========================================================================

Camada: painel_do_fogo:tb_evento  (polígonos = perímetros de queimada)

Decisões apoiadas na amostra real:
  - São ~6,8 milhões de eventos → SEMPRE filtrar (data/bbox) e paginar.
  - O servidor devolve coordenadas em EPSG:4674 (SIRGAS 2000). No Brasil, é
    praticamente idêntico ao 4326 (WGS84) — diferença de centímetros. Tratamos
    as coordenadas como lon/lat 4326 na ingestão; se for preciso rigor
    cartográfico, reprojetar no PostGIS com ST_Transform(geom, 4326).
  - Campos aproveitados: id -> external_id; dt_maxima -> occurred_at;
    o restante (qtd_deteccoes, area_km2, id_tipo_fogo, id_status_evento, ...)
    vai inteiro para 'properties' (JSONB).

Local sugerido:
    domain/services/ingestion/sipam_fogo_connector.py
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterator, Optional

from .source_connector import SourceConnector, GeoEventDTO, fetch_wfs_geojson

SIPAM_WFS_URL = "https://panorama.sipam.gov.br/geoserver/painel_do_fogo/ows"


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    """Converte strings ISO do SIPAM ('...Z', com ou sem frações) em datetime."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class SipamFogoConnector(SourceConnector):
    source = "sipam_fogo"
    event_type = "incendio"

    LAYER = "painel_do_fogo:tb_evento"
    GEOM_COLUMN = "geom"          # nome da coluna geométrica na fonte (visto na amostra)
    DATE_COLUMN = "dt_maxima"     # última detecção do evento

    def __init__(
        self,
        since_days: int = 7,
        bbox: Optional[str] = None,       # 'minx,miny,maxx,maxy' (lon/lat)
        page_size: int = 500,
        max_events: Optional[int] = 2000,
    ):
        self.since_days = since_days
        self.bbox = bbox
        self.page_size = page_size
        self.max_events = max_events

    def _cql(self) -> str:
        """Filtro CQL: eventos recentes (e, opcionalmente, dentro de um bbox)."""
        since = (datetime.now(timezone.utc) - timedelta(days=self.since_days)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        clauses = [f"{self.DATE_COLUMN} AFTER {since}"]
        if self.bbox:
            clauses.append(f"BBOX({self.GEOM_COLUMN}, {self.bbox})")
        return " AND ".join(clauses)

    def fetch(self) -> Iterator[GeoEventDTO]:
        start_index = 0
        yielded = 0

        while True:
            features = fetch_wfs_geojson(
                SIPAM_WFS_URL,
                self.LAYER,
                count=self.page_size,
                start_index=start_index,
                cql_filter=self._cql(),   # bbox vai dentro do CQL (não como param separado)
            )
            if not features:
                break

            for feature in features:
                props = feature.get("properties") or {}
                yield GeoEventDTO(
                    source=self.source,
                    external_id=str(feature.get("id")),
                    event_type=self.event_type,
                    geometry=feature.get("geometry"),
                    occurred_at=_parse_dt(props.get("dt_maxima") or props.get("dt_ultima_visao")),
                    properties=props,
                )
                yielded += 1
                if self.max_events is not None and yielded >= self.max_events:
                    return

            # Última página se veio menos que o tamanho pedido.
            if len(features) < self.page_size:
                break
            start_index += self.page_size
