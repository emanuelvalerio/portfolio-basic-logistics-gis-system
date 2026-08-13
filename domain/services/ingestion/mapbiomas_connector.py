"""
Conector do MapBiomas Alerta — desmatamento via API GraphQL v2
==============================================================

Herda de SourceConnector e devolve os mesmos GeoEventDTO das outras fontes.

Diferenças em relação ao SIPAM (WFS), todas ISOLADAS aqui dentro:
  - Autenticação por token (usa mapbiomas_client.get_mapbiomas_token()).
  - Consulta via GraphQL (POST com 'query'), não URL com parâmetros.
  - Geometria vem em WKT (texto). Convertemos WKT -> GeoJSON dentro do
    conector, para o DTO e o serviço de ingestão continuarem idênticos.

Campos usados (confirmados por introspecção do tipo AlertData):
  - alertCode  -> external_id   (o 'id' vem 0; o identificador real é alertCode)
  - detectedAt -> occurred_at
  - geometryWkt -> geometry (após WKT -> GeoJSON)
  - areaHa e demais -> properties

Local sugerido:
    domain/services/ingestion/mapbiomas_connector.py
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator, Optional

import requests
from shapely import wkt
from shapely.geometry import mapping

from .source_connector import SourceConnector, GeoEventDTO
from .mapbiomas_client import get_mapbiomas_token, MAPBIOMAS_GRAPHQL_URL

# Query dos alertas. Pedimos poucos campos + a geometria (que é pesada).
_ALERTS_QUERY = """
query alerts($startDate: BaseDate, $limit: Int, $page: Int) {
  alerts(startDate: $startDate, limit: $limit, page: $page) {
    collection {
      alertCode
      areaHa
      detectedAt
      statusName
      geometryWkt
    }
  }
}
"""


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    """detectedAt vem como 'YYYY-MM-DD'."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class MapBiomasConnector(SourceConnector):
    source = "mapbiomas"
    event_type = "desmatamento"

    def __init__(
        self,
        start_detected_at: Optional[str] = None,  # 'YYYY-MM-DD' (só alertas a partir dessa data)
        page_size: int = 25,                      # geometria é pesada -> páginas pequenas
        max_alerts: Optional[int] = 100,
        timeout: int = 120,
    ):
        self.start_detected_at = start_detected_at
        self.page_size = page_size
        self.max_alerts = max_alerts
        self.timeout = timeout
        self._token: Optional[str] = None

    def _headers(self) -> dict:
        if self._token is None:
            self._token = get_mapbiomas_token()
        return {"Authorization": f"Bearer {self._token}"}

    def _fetch_page(self, page: int) -> list[dict]:
        variables = {
            "startDate": self.start_detected_at,
            "limit": self.page_size,
            "page": page,
        }
        response = requests.post(
            MAPBIOMAS_GRAPHQL_URL,
            json={"query": _ALERTS_QUERY, "variables": variables},
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        if "errors" in data:
            raise RuntimeError(f"Erro na query MapBiomas: {data['errors']}")
        return data["data"]["alerts"]["collection"]

    def fetch(self) -> Iterator[GeoEventDTO]:
        page = 1
        yielded = 0

        while True:
            alerts = self._fetch_page(page=page)
            if not alerts:
                break

            for alert in alerts:
                wkt_text = alert.get("geometryWkt")
                if not wkt_text:
                    continue

                # A ÚNICA novidade: WKT (texto) -> objeto shapely -> dict GeoJSON.
                geometry = mapping(wkt.loads(wkt_text))

                # O WKT também vai para properties, mas removemos do bloco principal
                # para não duplicar um texto gigante no JSONB.
                props = {k: v for k, v in alert.items() if k != "geometryWkt"}

                yield GeoEventDTO(
                    source=self.source,
                    external_id=str(alert.get("alertCode")),
                    event_type=self.event_type,
                    geometry=geometry,
                    occurred_at=_parse_dt(alert.get("detectedAt")),
                    properties=props,
                )
                yielded += 1
                if self.max_alerts is not None and yielded >= self.max_alerts:
                    return

            if len(alerts) < self.page_size:
                break
            page += 1
