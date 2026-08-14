"""
Conector do SNIRH/ANA — recursos hídricos via ArcGIS REST
=========================================================

PARAMETRIZADO: um único conector serve para VÁRIAS camadas do SNIRH
(estações = ponto, hidrografia = linha, etc.). Diferente do SIPAM/MapBiomas
(fonte homogênea), cada camada aqui tem campos totalmente diferentes — então
o conector recebe, por parâmetro, QUAL campo é o id e QUAL é a data.

Diferenças em relação ao SIPAM (WFS), isoladas aqui:
  - É ArcGIS REST, não GeoServer: a consulta é
    .../MapServer/<layer_id>/query?where=1=1&outFields=*&f=geojson
  - Já devolve GeoJSON (dict), como o WFS — então NÃO precisa de shapely aqui.

Local sugerido:
    domain/services/ingestion/snirh_connector.py
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator, Optional

import requests

from .source_connector import SourceConnector, GeoEventDTO

SNIRH_BASE = "https://portal1.snirh.gov.br/server/rest/services/dados_abertos"


def _parse_epoch_ms(value) -> Optional[datetime]:
    """Alguns campos de data do ArcGIS vêm como epoch em milissegundos."""
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
    except (ValueError, TypeError, OSError):
        return None


class SnirhConnector(SourceConnector):
    source = "snirh"

    def __init__(
        self,
        service: str,                 # ex.: "Estacao_Fluviometrica"
        event_type: str,              # ex.: "estacao_fluviometrica" (rótulo desta camada)
        id_field: str,                # campo que vira external_id (ex.: "CODIGO")
        date_field: Optional[str] = None,      # campo de data, se houver (ex.: "ULTIMAATUALIZACAO")
        layer_id: int = 0,
        page_size: int = 500,
        max_records: Optional[int] = 1000,
        timeout: int = 60,
    ):
        self.service = service
        self.event_type = event_type          # sobrescreve o atributo de classe por instância
        self.id_field = id_field
        self.date_field = date_field
        self.layer_id = layer_id
        self.page_size = page_size
        self.max_records = max_records
        self.timeout = timeout

    def _fetch_page(self, offset: int) -> list[dict]:
        url = f"{SNIRH_BASE}/{self.service}/MapServer/{self.layer_id}/query"
        params = {
            "where": "1=1",
            "outFields": "*",
            "outSR": "4326",            # pede as coordenadas em WGS84
            "f": "geojson",
            "resultRecordCount": self.page_size,
            "resultOffset": offset,     # paginação do ArcGIS
        }
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json().get("features", [])

    def fetch(self) -> Iterator[GeoEventDTO]:
        offset = 0
        yielded = 0

        while True:
            features = self._fetch_page(offset)
            if not features:
                break

            for f in features:
                props = f.get("properties") or {}
                geometry = f.get("geometry")
                if not geometry:
                    continue

                # AQUI está a parametrização: o id e a data vêm de campos
                # indicados por parâmetro, porque cada camada os nomeia diferente.
                external_id = str(props.get(self.id_field))
                occurred_at = _parse_epoch_ms(props.get(self.date_field)) if self.date_field else None

                yield GeoEventDTO(
                    source=self.source,
                    external_id=external_id,
                    event_type=self.event_type,
                    geometry=geometry,
                    occurred_at=occurred_at,
                    properties=props,
                )
                yielded += 1
                if self.max_records is not None and yielded >= self.max_records:
                    return

            if len(features) < self.page_size:
                break
            offset += self.page_size
