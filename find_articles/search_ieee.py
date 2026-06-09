import os
import time

import requests

from common import BLOCK_MED, BLOCK_QML, normalize_text, write_results


QUERY = f"({BLOCK_QML}) AND ({BLOCK_MED})"


def _check_api_key(api_key):
    """Faz uma requisição mínima para validar a chave antes de iniciar a coleta."""
    response = requests.get(
        "https://ieeexploreapi.ieee.org/api/v1/search/articles",
        params={"apikey": api_key, "querytext": "quantum", "max_records": 1, "format": "json"},
        timeout=30,
    )
    if response.status_code == 403:
        raise RuntimeError(
            "IEEE retornou 403 Forbidden.\n"
            "Possíveis causas:\n"
            "  1. Chave inválida ou ainda não aprovada — verifique pasta de spam e aguarde\n"
            "     até 24 h após o cadastro em https://developer.ieee.org/\n"
            "  2. Conta ainda pendente de aprovação manual pela IEEE.\n"
            "Se o e-mail de confirmação não chegou:\n"
            "  - Tente reenviar em https://developer.ieee.org/ (opção 'Resend verification')\n"
            "  - Ou contate xploreapi@ieee.org informando seu e-mail de cadastro."
        )
    if response.status_code == 401:
        raise RuntimeError("IEEE retornou 401: chave de API incorreta.")
    response.raise_for_status()


def search_ieee(query=QUERY, batch_size=200, sleep_seconds=1.0):
    api_key = os.getenv("IEEE_API_KEY")
    if not api_key:
        raise RuntimeError("Defina a variável de ambiente IEEE_API_KEY.")

    _check_api_key(api_key)

    base_url = "https://ieeexploreapi.ieee.org/api/v1/search/articles"
    start_record = 1
    rows = []

    while True:
        response = requests.get(
            base_url,
            params={
                "apikey": api_key,
                "querytext": query,
                "start_record": start_record,
                "max_records": batch_size,
                "format": "json",
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()

        total_records = payload.get("total_records", 0)
        articles = payload.get("articles", [])

        if not articles:
            break

        for article in articles:
            authors = article.get("authors", {}).get("authors", [])
            rows.append(
                {
                    "article_number": article.get("article_number", ""),
                    "title": normalize_text(article.get("title")),
                    "authors": ", ".join(
                        a.get("full_name", "") for a in authors if a.get("full_name")
                    ),
                    "publication_year": article.get("publication_year", ""),
                    "publication_title": article.get("publication_title", ""),
                    "doi": article.get("doi", ""),
                    "abstract": normalize_text(article.get("abstract")),
                    "html_url": article.get("html_url", ""),
                    "pdf_url": article.get("pdf_url", ""),
                }
            )

        print(f"[ieee] {len(rows)}/{total_records} artigos coletados…")

        if len(rows) >= total_records:
            break

        start_record += len(articles)
        time.sleep(sleep_seconds)

    return write_results(rows, ["article_number", "doi"], "ieee_QML_medicine_results.csv")


if __name__ == "__main__":
    output, count = search_ieee()
    print(f"[ieee] CSV gerado em {output} com {count} artigos.")
