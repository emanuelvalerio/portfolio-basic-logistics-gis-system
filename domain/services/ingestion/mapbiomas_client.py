"""
Cliente de autenticação do MapBiomas Alerta (API GraphQL v2)
============================================================

Responsabilidade única: fazer login (mutation signIn) e devolver o token.
O token é usado depois, no cabeçalho Authorization, para consultar os alertas.

As credenciais vêm do .env (MAPBIOMAS_EMAIL / MAPBIOMAS_PASSWORD),
NUNCA escritas no código.

Local sugerido:
    domain/services/ingestion/mapbiomas_client.py
"""

from __future__ import annotations

import os
import requests

MAPBIOMAS_GRAPHQL_URL = "https://plataforma.alerta.mapbiomas.org/api/v2/graphql"

# Query GraphQL de login. Repare que é um TEXTO: dizemos a operação (signIn),
# quais argumentos passamos ($email, $password) e qual campo queremos de volta (token).
_SIGN_IN_MUTATION = """
mutation signIn($email: String!, $password: String!) {
  signIn(email: $email, password: $password) {
    token
  }
}
"""


def get_mapbiomas_token(timeout: int = 30) -> str:
    """Faz login no MapBiomas e devolve o token (Bearer)."""
    email = os.getenv("MAPBIOMAS_EMAIL")
    password = os.getenv("MAPBIOMAS_PASSWORD")
    if not email or not password:
        raise RuntimeError(
            "Credenciais ausentes: defina MAPBIOMAS_EMAIL e MAPBIOMAS_PASSWORD no .env"
        )

    # No GraphQL, mandamos um POST com 'query' (o texto) e 'variables' (os valores).
    payload = {
        "query": _SIGN_IN_MUTATION,
        "variables": {"email": email, "password": password},
    }

    response = requests.post(MAPBIOMAS_GRAPHQL_URL, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()

    # O GraphQL devolve erros dentro do corpo (não como HTTP 500), então checamos.
    if "errors" in data:
        raise RuntimeError(f"Erro no login MapBiomas: {data['errors']}")

    token = data["data"]["signIn"]["token"]
    return token
