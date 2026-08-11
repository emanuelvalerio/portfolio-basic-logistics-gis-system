"""
Sonda de descoberta do MapBiomas Alerta
=======================================

NÃO é o conector final — é investigação. Duas partes:

  1) INTROSPECÇÃO: pergunta ao GraphQL QUAIS campos o tipo 'AlertData' tem.
     (A API descreve a si mesma — é como pedir o "índice" do schema.)
  2) AMOSTRA: pede 2 alertas com os campos simples que já sabemos existir.

Rodar da raiz do repositório:
    POSTGRES_HOST=localhost python3 -m domain.services.ingestion.mapbiomas_probe
"""

from __future__ import annotations

import json
from dotenv import load_dotenv
import requests

from domain.services.ingestion.mapbiomas_client import (
    get_mapbiomas_token,
    MAPBIOMAS_GRAPHQL_URL,
)

# 1) Introspecção: lista os campos disponíveis no tipo AlertData.
_INTROSPECT_QUERY = """
query {
  __type(name: "AlertData") {
    fields {
      name
      type { name kind ofType { name kind } }
    }
  }
}
"""

# 2) Amostra só com os campos simples que provavelmente passaram.
_SAMPLE_QUERY = """
query {
  alerts(limit: 2) {
    collection {
      id
      alertCode
      areaHa
      detectedAt
    }
  }
}
"""


def _post(token: str, query: str) -> dict:
    response = requests.post(
        MAPBIOMAS_GRAPHQL_URL,
        json={"query": query},
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    load_dotenv()
    token = get_mapbiomas_token()

    print("=" * 60)
    print("CAMPOS DISPONÍVEIS NO TIPO 'AlertData':")
    print("=" * 60)
    introspection = _post(token, _INTROSPECT_QUERY)
    fields = introspection.get("data", {}).get("__type", {}).get("fields")
    if fields:
        for f in fields:
            t = f["type"]
            type_name = t.get("name") or (t.get("ofType") or {}).get("name") or t.get("kind")
            print(f"  - {f['name']:<28} ({type_name})")
    else:
        print(json.dumps(introspection, indent=2, ensure_ascii=False)[:1500])

    print()
    print("=" * 60)
    print("AMOSTRA (campos simples):")
    print("=" * 60)
    sample = _post(token, _SAMPLE_QUERY)
    print(json.dumps(sample, indent=2, ensure_ascii=False)[:2000])


if __name__ == "__main__":
    main()
