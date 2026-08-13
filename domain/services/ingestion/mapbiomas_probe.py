"""
Sonda de descoberta do MapBiomas Alerta
=======================================

Agora investiga os ARGUMENTOS que o campo 'alerts' aceita (paginação/filtro).
A API se descreve: perguntamos o tipo 'Query' e, dentro dele, o campo 'alerts'
e seus 'args'. É assim que achamos os nomes certos de limit/offset/data.

Rodar da raiz:
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

# Pergunta: no tipo raiz 'Query', quais argumentos o campo 'alerts' aceita?
_ARGS_QUERY = """
query {
  __type(name: "Query") {
    fields {
      name
      args {
        name
        type { name kind ofType { name kind } }
      }
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

    result = _post(token, _ARGS_QUERY)
    fields = result.get("data", {}).get("__type", {}).get("fields", []) or []

    # Filtra só o campo 'alerts' e mostra seus argumentos.
    for field in fields:
        if field["name"] == "alerts":
            print("=" * 55)
            print("ARGUMENTOS ACEITOS PELO CAMPO 'alerts':")
            print("=" * 55)
            for arg in field.get("args", []):
                t = arg["type"]
                type_name = t.get("name") or (t.get("ofType") or {}).get("name") or t.get("kind")
                print(f"  - {arg['name']:<24} ({type_name})")
            return

    print("Campo 'alerts' não encontrado. Resposta crua:")
    print(json.dumps(result, indent=2, ensure_ascii=False)[:1500])


if __name__ == "__main__":
    main()
