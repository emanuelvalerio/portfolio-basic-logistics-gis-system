"""
Base de ingestão de fontes geoespaciais
=======================================

Peças reutilizáveis, independentes de qualquer fonte específica:

- GeoEventDTO      : o "pacote" normalizado que todo conector produz.
- SourceConnector  : o contrato que toda fonte implementa.
- fetch_wfs_geojson: cliente genérico para GeoServer WFS (padrão OGC),
                     com paginação (startIndex) e filtros (count/bbox/cql).

Sugestão de local no repositório:
    domain/services/ingestion/source_connector.py
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterator, Optional

import requests


@dataclass
class GeoEventDTO:
    """
    Representação normalizada de um evento, ANTES de virar linha no banco.
    A geometria viaja como dicionário GeoJSON; a conversão para o tipo do
    PostGIS acontece no serviço de ingestão, mantendo o conector simples.
    """
    source: str                 # 'sipam_fogo', 'snirh', ...
    external_id: str            # id do evento na fonte de origem
    event_type: str             # 'incendio', 'seguranca_hidrica', ...
    geometry: dict              # geometria em GeoJSON (dict)
    occurred_at: Optional[datetime] = None
    properties: dict[str, Any] = field(default_factory=dict)


class SourceConnector(ABC):
    """Contrato comum: toda fonte sabe se identificar e produzir GeoEventDTOs."""
    source: str
    event_type: str

    @abstractmethod
    def fetch(self) -> Iterator[GeoEventDTO]:
        raise NotImplementedError


def fetch_wfs_geojson(
    base_url: str,
    type_name: str,
    *,
    count: Optional[int] = None,
    start_index: Optional[int] = None,
    bbox: Optional[str] = None,
    cql_filter: Optional[str] = None,
    version: str = "2.0.0",
    timeout: int = 60,
) -> list[dict]:
    """
    Consulta um GeoServer WFS e devolve a lista de 'features' (GeoJSON).

    Parâmetros de paginação/filtro:
      - count       : nº máximo de feições por página
      - start_index : deslocamento para paginar (0, count, 2*count, ...)
      - bbox        : recorte 'minx,miny,maxx,maxy' (não combine com cql_filter)
      - cql_filter  : filtro CQL, ex. "dt_maxima AFTER 2026-08-01T00:00:00Z"

    Padrão OGC: request=GetFeature + outputFormat=application/json.
    """
    params: dict[str, Any] = {
        "service": "WFS",
        "version": version,
        "request": "GetFeature",
        "typeName": type_name,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
    }
    if count is not None:
        params["count"] = count
    if start_index is not None:
        params["startIndex"] = start_index
    if bbox is not None:
        params["bbox"] = bbox
    if cql_filter is not None:
        params["cql_filter"] = cql_filter

    response = requests.get(base_url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json().get("features", [])
